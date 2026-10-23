static uint8_t calc_duty_from_curve(fan_instance_t *fan, int16_t temp)
{
    if (fan->config.curve_points == 0) {
        return fan->config.max_duty;
    }
    
    const ts_fan_curve_point_t *curve = fan->config.curve;
    uint8_t points = fan->config.curve_points;
    
    // 低于最低点
    if (temp <= curve[0].temp) {
        return curve[0].duty;
    }
    
    // 高于最高点
    if (temp >= curve[points - 1].temp) {
        return curve[points - 1].duty;
    }
    
    // 线性插值
    for (int i = 0; i < points - 1; i++) {
        if (temp >= curve[i].temp && temp < curve[i + 1].temp) {
            int32_t t_range = curve[i + 1].temp - curve[i].temp;
            int32_t d_range = (int32_t)curve[i + 1].duty - (int32_t)curve[i].duty;
            int32_t t_offset = temp - curve[i].temp;
            return curve[i].duty + (uint8_t)((t_offset * d_range) / t_range);
        }
    }
    
    return fan->config.max_duty;
}

static float clamp_float(float value, float min_value, float max_value)
{
    if (value < min_value) return min_value;
    if (value > max_value) return max_value;
    return value;
}

static uint8_t apply_duty_limits(fan_instance_t *fan, uint8_t target)
{
    if (target < fan->config.min_duty && target > 0) {
        target = fan->config.min_duty;
    }
    if (target > fan->config.max_duty) {
        target = fan->config.max_duty;
    }
    return target;
}

static bool is_temp_data_basic_valid(const ts_temp_data_t *data)
{
    if (!data ||
        !data->valid ||
        data->source == TS_TEMP_SOURCE_DEFAULT ||
        data->value < TS_TEMP_MIN_VALID ||
        data->value > TS_TEMP_MAX_VALID) {
        return false;
    }

    return true;
}

static bool is_auto_temp_data_usable(const ts_temp_data_t *data)
{
    if (!is_temp_data_basic_valid(data)) {
        return false;
    }

    if (data->bound_total_count > 0 &&
        (data->partial_stale || data->bound_valid_count < data->bound_total_count)) {
        return false;
    }

    return true;
}

static void reset_adaptive_auto_state(fan_instance_t *fan)
{
    fan->target_duty = fan->current_duty;
    fan->control_temperature = fan->temperature;
    fan->guard_temperature = fan->temperature;
    fan->predicted_temperature = fan->temperature;
    fan->slope_c_per_min = 0.0f;
    fan->controller_gain = FAN_AUTO_GAIN_DEFAULT;
    fan->cooling_response = 0.0f;
    fan->auto_state = TS_FAN_AUTO_STATE_IDLE;
    fan->guard_active = false;
    fan->temp_stale = false;
    fan->guard_release_since_ms = 0;
    fan->guard_last_observation_ms = 0;
    fan->guard_last_report_ms = 0;
    fan->response_observing = false;
    fan->response_until_ms = 0;
    fan->response_slope_before = 0.0f;
    memset(fan->temp_history, 0, sizeof(fan->temp_history));
    fan->temp_history_next = 0;
    fan->temp_history_count = 0;
    fan->last_auto_update_ms = 0;
    fan->auto_fall_credit = 0.0f;
}

static bool get_adaptive_temperatures(const ts_temp_data_t *temp_data,
                                      int16_t *control_temp,
                                      int16_t *guard_temp)
{
    if (!control_temp || !guard_temp || !is_auto_temp_data_usable(temp_data)) {
        return false;
    }

    *control_temp = temp_data->value;
    if (temp_data->guard_valid &&
        temp_data->guard_value >= TS_TEMP_MIN_VALID &&
        temp_data->guard_value <= TS_TEMP_MAX_VALID) {
        *guard_temp = temp_data->guard_value;
    } else {
        *guard_temp = temp_data->value;
    }

    return true;
}

static void record_auto_temp_sample(fan_instance_t *fan, int16_t temp, int64_t now_ms)
{
    fan->temp_history[fan->temp_history_next].temp = temp;
    fan->temp_history[fan->temp_history_next].timestamp_ms = now_ms;
    fan->temp_history[fan->temp_history_next].valid = true;
    fan->temp_history_next = (fan->temp_history_next + 1) % FAN_AUTO_HISTORY_SIZE;
    if (fan->temp_history_count < FAN_AUTO_HISTORY_SIZE) {
        fan->temp_history_count++;
    }
}

static bool calculate_auto_slope(fan_instance_t *fan, int16_t current_temp,
                                 int64_t now_ms, uint32_t min_span_ms,
                                 float *slope_c_per_min)
{
    const fan_temp_sample_t *oldest = NULL;
    int64_t oldest_age = 0;

    if (!fan || !slope_c_per_min || fan->temp_history_count == 0) {
        return false;
    }

    for (uint8_t i = 0; i < fan->temp_history_count; i++) {
        const fan_temp_sample_t *sample = &fan->temp_history[i];
        if (!sample->valid) {
            continue;
        }
        int64_t age = now_ms - sample->timestamp_ms;
        if (age < 0 || age > FAN_AUTO_SLOPE_WINDOW_MS) {
            continue;
        }
        if (!oldest || age > oldest_age) {
            oldest = sample;
            oldest_age = age;
        }
    }

    if (!oldest || oldest_age < min_span_ms) {
        return false;
    }

    float delta_c = (current_temp - oldest->temp) / 10.0f;
    *slope_c_per_min = delta_c * 60000.0f / (float)oldest_age;
    return true;
}

static uint8_t apply_auto_rate_limit(fan_instance_t *fan, uint8_t target,
                                     bool allow_down, int64_t now_ms)
{
    uint8_t current = fan->current_duty;
    float dt_sec = 1.0f;
    if (fan->last_auto_update_ms > 0) {
        dt_sec = (now_ms - fan->last_auto_update_ms) / 1000.0f;
    }
    if (dt_sec <= 0.0f) {
        dt_sec = 1.0f;
    }

    if (target > current) {
        fan->auto_fall_credit = 0.0f;
        uint8_t max_step = (uint8_t)(FAN_AUTO_RISE_RATE_PER_SEC * dt_sec + 0.5f);
        if (max_step < 1) max_step = 1;
        if ((uint16_t)target > (uint16_t)current + max_step) {
            target = current + max_step;
        }
        if (current == 0 && target > 0 &&
            target < fan->config.min_duty) {
            target = fan->config.min_duty;
        }
    } else if (target < current) {
        if (!allow_down) {
            fan->auto_fall_credit = 0.0f;
            target = current;
        } else {
            /* 已不需要的额外风量按温度趋势窗口平滑退出，避免峰值留下数分钟尾巴。
             * 接近当前需求时仍使用原来的慢速退档；升档和退档许可保持不变。 */
            float excess_rate = (current - target) / (FAN_AUTO_SLOPE_WINDOW_MS / 1000.0f);
            float fall_rate = excess_rate > FAN_AUTO_FALL_RATE_PER_SEC
                            ? excess_rate : FAN_AUTO_FALL_RATE_PER_SEC;
            fan->auto_fall_credit += fall_rate * dt_sec;
            uint8_t desired_step = current - target;
            uint8_t max_step = fan->auto_fall_credit >= desired_step
                             ? desired_step : (uint8_t)fan->auto_fall_credit;
            if (max_step == 0) {
                target = current;
            } else {
                target = current - max_step;
                /* Permission belongs to this outstanding demand, not a later one. */
                fan->auto_fall_credit = max_step == desired_step
                                      ? 0.0f : fan->auto_fall_credit - max_step;
            }
        }
    } else {
        fan->auto_fall_credit = 0.0f;
    }

    fan->last_auto_update_ms = now_ms;
    return target;
}

static void update_response_learning(fan_instance_t *fan, bool slope_valid,
                                     float slope, int64_t now_ms)
{
    if (!fan->response_observing || now_ms < fan->response_until_ms) {
        return;
    }

    fan->response_observing = false;
    if (!slope_valid) {
        return;
    }

    fan->cooling_response = fan->response_slope_before - slope;
    if (fan->cooling_response < 0.2f) {
        fan->controller_gain *= 1.15f;
    } else if (fan->cooling_response > 1.5f || slope < -0.5f) {
        fan->controller_gain *= 0.95f;
    }
    fan->controller_gain = clamp_float(fan->controller_gain,
                                       FAN_AUTO_GAIN_MIN,
                                       FAN_AUTO_GAIN_MAX);
}

static void update_guard_observation(fan_instance_t *fan, const ts_temp_data_t *data,
                                     int64_t now_ms)
{
    /* Valid cached readings count; a missed evaluation or changed source does not.
     * Two timer periods allow normal scheduling jitter, capped by input validity. */
    int64_t max_gap_ms = 2LL * CONFIG_TS_DRIVERS_FAN_TEMP_UPDATE_MS;
    if (max_gap_ms > TS_TEMP_DATA_TIMEOUT_MS) max_gap_ms = TS_TEMP_DATA_TIMEOUT_MS;
    bool broken = fan->guard_last_observation_ms == 0 ||
                  now_ms <= fan->guard_last_observation_ms ||
                  now_ms - fan->guard_last_observation_ms > max_gap_ms ||
                  data->source != fan->guard_last_source ||
                  data->identity_revision != fan->guard_last_identity ||
                  data->timestamp_ms < fan->guard_last_report_ms ||
                  data->timestamp_ms - fan->guard_last_report_ms > TS_TEMP_DATA_TIMEOUT_MS ||
                  data->timestamp_ms <= 0 || data->timestamp_ms > now_ms;
    if (broken) fan->guard_release_since_ms = 0;
    fan->guard_last_observation_ms = now_ms;
    fan->guard_last_report_ms = data->timestamp_ms;
    fan->guard_last_source = data->source;
    fan->guard_last_identity = data->identity_revision;
}

/* Isolated proposal. No production source is modified.
 * Engineering initial values: 5 s +/- one 1 s timer tick / 0.3 C cooling, 3 new reports,
 * cancel at +0.2 C between reports or across the recent ~2 s history;
 * extra permission only below 70 C / 85 C forecast.
 * The original demand, gain update, rate limiter and protection stay intact. */
typedef struct {
    bool initialized, open;
    int64_t last_report_ms, confidence_since_ms;
    int16_t last_temp;
    uint8_t fresh_count;
    ts_temp_source_type_t source;
    uint32_t identity;
} extra_release_state_t;
static extra_release_state_t release_state;
static void reset_extra_release(void) { memset(&release_state, 0, sizeof(release_state)); }

static bool extra_release(fan_instance_t *fan, const ts_temp_data_t *data,
                          uint8_t demand, uint8_t baseline, int64_t now)
{
    extra_release_state_t *s = &release_state; /* One fan in this isolated harness. */
    bool risk = fan->guard_active || fan->guard_temperature >= 700 ||
                fan->predicted_temperature >= 850 || fan->fault || !fan->duty_valid;
    if (risk || !data || !is_auto_temp_data_usable(data) || data->timestamp_ms > now ||
        now - data->timestamp_ms > 2LL * CONFIG_TS_DRIVERS_FAN_TEMP_UPDATE_MS) {
        reset_extra_release();
        return false;
    }
    bool broken = !s->initialized || data->source != s->source ||
                  data->identity_revision != s->identity ||
                  data->timestamp_ms < s->last_report_ms ||
                  data->timestamp_ms - s->last_report_ms > 2LL * CONFIG_TS_DRIVERS_FAN_TEMP_UPDATE_MS;
    if (broken) {
        reset_extra_release();
        s->initialized = true;
        s->last_report_ms = data->timestamp_ms;
        s->confidence_since_ms = now;
        s->last_temp = fan->control_temperature;
        s->fresh_count = 1;
        s->source = data->source;
        s->identity = data->identity_revision;
        return false;
    }
    if (data->timestamp_ms > s->last_report_ms) {
        bool reheated = fan->control_temperature - s->last_temp >= 2;
        for (unsigned i = 0; i < FAN_AUTO_HISTORY_SIZE; ++i) {
            fan_temp_sample_t *p = &fan->temp_history[i];
            int64_t age = now - p->timestamp_ms;
            if (p->valid && age >= 1000 && age <= 3000 &&
                p->timestamp_ms >= s->confidence_since_ms &&
                fan->control_temperature - p->temp >= 2) reheated = true;
        }
        if (reheated) {
            s->open = false;             /* Fresh reheating cancels on this cycle. */
            s->confidence_since_ms = now;
            s->fresh_count = 1;
        } else if (s->fresh_count < 3) {
            ++s->fresh_count;
        }
        s->last_report_ms = data->timestamp_ms;
        s->last_temp = fan->control_temperature;
    }
    if (demand >= fan->current_duty || baseline >= fan->current_duty) {
        s->open = false;                 /* No outstanding extra output to retire. */
        return false;
    }
    int64_t oldest = now;
    int16_t old_temp = fan->control_temperature;
    for (unsigned i = 0; i < FAN_AUTO_HISTORY_SIZE; ++i) {
        fan_temp_sample_t *p = &fan->temp_history[i];
        int64_t age = now - p->timestamp_ms;
        if (p->valid && age >= 0 && age <= 6000 && p->timestamp_ms >= s->confidence_since_ms &&
            p->timestamp_ms < oldest) {
            oldest = p->timestamp_ms;
            old_temp = p->temp;
        }
    }
    if (s->fresh_count >= 3 && now - oldest >= 4000 &&
        old_temp - fan->control_temperature >= 3) s->open = true;
    return s->open;
}

static esp_err_t apply_adaptive_auto(fan_instance_t *fan, const ts_temp_data_t *temp_data)
{
    int64_t now_ms = esp_timer_get_time() / 1000;
    int16_t control_temp = TS_TEMP_DEFAULT_VALUE;
    int16_t guard_temp = TS_TEMP_DEFAULT_VALUE;
    uint8_t old_duty = fan->current_duty;
    bool recovered_from_stale = fan->temp_stale;

    if (!get_adaptive_temperatures(temp_data, &control_temp, &guard_temp)) {
        fan->temp_stale = true;
        reset_extra_release();
        fan->auto_state = TS_FAN_AUTO_STATE_STALE;
        fan->response_observing = false;
        fan->auto_fall_credit = 0.0f;
        fan->guard_active = false;
        fan->guard_release_since_ms = 0;
        fan->guard_last_observation_ms = 0;
        fan->target_duty = FAN_AUTO_STALE_DUTY;
        fan->predicted_temperature = fan->control_temperature;
        fan->last_auto_update_ms = now_ms;
        return update_pwm(fan, FAN_AUTO_STALE_DUTY);
    }

    fan->temp_stale = false;
    fan->temperature = control_temp;
    fan->control_temperature = control_temp;
    fan->guard_temperature = guard_temp;
    record_auto_temp_sample(fan, control_temp, now_ms);

    update_guard_observation(fan, temp_data, now_ms);
    if (guard_temp >= FAN_AUTO_GUARD_TEMP) {
        fan->guard_active = true;
        fan->guard_release_since_ms = 0;
    } else if (fan->guard_active) {
        if (guard_temp <= FAN_AUTO_GUARD_RELEASE_TEMP) {
            if (fan->guard_release_since_ms == 0) {
                fan->guard_release_since_ms = now_ms;
            } else if ((now_ms - fan->guard_release_since_ms) >= FAN_AUTO_GUARD_RELEASE_MS) {
                fan->guard_active = false;
                fan->guard_release_since_ms = 0;
            }
        } else {
            fan->guard_release_since_ms = 0;
        }
    }

    bool slope_valid = calculate_auto_slope(fan, control_temp, now_ms,
                                            FAN_AUTO_MIN_SAMPLE_MS,
                                            &fan->slope_c_per_min);
    if (!slope_valid) {
        fan->slope_c_per_min = 0.0f;
    }
    update_response_learning(fan, slope_valid, fan->slope_c_per_min, now_ms);

    if (fan->guard_active) {
        reset_extra_release();
        fan->auto_state = TS_FAN_AUTO_STATE_GUARD;
        fan->response_observing = false;
        fan->auto_fall_credit = 0.0f;
        fan->target_duty = 100;
        fan->predicted_temperature = guard_temp;
        fan->last_auto_update_ms = now_ms;
        return update_pwm(fan, 100);
    }

    uint8_t baseline = apply_duty_limits(fan, calc_duty_from_curve(fan, control_temp));
    uint8_t target = baseline;

    if (slope_valid) {
        float predicted = control_temp + (fan->slope_c_per_min * (FAN_AUTO_PREDICT_WINDOW_SEC / 60.0f) * 10.0f);
        if (predicted < TS_TEMP_MIN_VALID) predicted = TS_TEMP_MIN_VALID;
        if (predicted > TS_TEMP_MAX_VALID) predicted = TS_TEMP_MAX_VALID;
        fan->predicted_temperature = (int16_t)predicted;

        if (fan->predicted_temperature >= FAN_AUTO_GUARD_TEMP) {
            fan->auto_state = TS_FAN_AUTO_STATE_GUARD;
            target = fan->config.max_duty;
        } else {
            float boost = 0.0f;
            float margin_c = (FAN_AUTO_GUARD_TEMP - guard_temp) / 10.0f;
            if (margin_c < 25.0f) {
                boost += (25.0f - margin_c) * 1.2f;
            }
            if (fan->predicted_temperature > 850) {
                boost += ((fan->predicted_temperature - 850) / 10.0f) * 1.5f;
            }
            if (fan->slope_c_per_min > 0.0f) {
                boost += fan->slope_c_per_min * 2.0f;
            }

            float adaptive_target = baseline + boost * fan->controller_gain;
            if (adaptive_target > 100.0f) adaptive_target = 100.0f;
            target = apply_duty_limits(fan, (uint8_t)(adaptive_target + 0.5f));
            fan->auto_state = TS_FAN_AUTO_STATE_ACTIVE;
        }
    } else {
        fan->predicted_temperature = control_temp;
        fan->auto_state = TS_FAN_AUTO_STATE_BASELINE;
    }

    bool allow_down = (guard_temp <= FAN_AUTO_GUARD_RELEASE_TEMP) &&
                      (!slope_valid || fan->slope_c_per_min <= 0.0f);
    observed_baseline = baseline;
    observed_demand = target;
    observed_original_permission = allow_down;
    if (use_release && !allow_down) {
        observed_extra_permission = extra_release(fan, temp_data, target, baseline, now_ms);
        allow_down = allow_down || observed_extra_permission;
    } else {
        release_state.open = false;
    }
    if (target < fan->current_duty && !allow_down && !recovered_from_stale) {
        target = fan->current_duty;
    }

    if (recovered_from_stale && target < fan->current_duty) {
        fan->auto_fall_credit = 0.0f;
        fan->last_auto_update_ms = now_ms;
    } else {
        target = apply_auto_rate_limit(fan, target, allow_down, now_ms);
    }
    fan->target_duty = target;
    esp_err_t ret = update_pwm(fan, target);

    if (ret == ESP_OK && !fan->response_observing && slope_valid &&
        target >= old_duty + FAN_AUTO_RESPONSE_DUTY_DELTA) {
        fan->response_observing = true;
        fan->response_until_ms = now_ms + FAN_AUTO_RESPONSE_WINDOW_MS;
        fan->response_slope_before = fan->slope_c_per_min;
    }

    return ret;
}

static esp_err_t update_pwm(fan_instance_t *fan, uint8_t duty)
{
    if (!fan->pwm) {
        return ESP_ERR_INVALID_STATE;
    }
    
    if (!fan->enabled) {
        duty = 0;
    }
    
    if (duty > 100) duty = 100;
    
    // PWM 反转
    uint8_t actual = fan->config.invert_pwm ? (100 - duty) : duty;
    
    esp_err_t ret = ts_pwm_set_duty(fan->pwm, (float)actual);
    if (ret == ESP_OK) {
        fan->current_duty = duty;
        fan->duty_valid = true;
        fan->fault = false;
    } else {
        fan->fault = true;
    }
    
    return ret;
}