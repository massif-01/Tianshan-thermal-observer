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
