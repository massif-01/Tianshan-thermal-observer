#define FAN_AUTO_GUARD_TEMP            950     /* 95.0°C */
#define FAN_AUTO_GUARD_RELEASE_TEMP    900     /* 90.0°C */
#define FAN_AUTO_GUARD_RELEASE_MS      30000
#define FAN_AUTO_PREDICT_WINDOW_SEC    45.0f
#define FAN_AUTO_SLOPE_WINDOW_MS       30000
#define FAN_AUTO_MIN_SAMPLE_MS         10000
#define FAN_AUTO_RESPONSE_WINDOW_MS    30000
#define FAN_AUTO_RESPONSE_DUTY_DELTA   5
#define FAN_AUTO_GAIN_DEFAULT          0.75f
#define FAN_AUTO_GAIN_MIN              0.50f
#define FAN_AUTO_GAIN_MAX              2.00f
#define FAN_AUTO_RISE_RATE_PER_SEC     12.0f
#define FAN_AUTO_FALL_RATE_PER_SEC     0.30f
#define FAN_AUTO_STALE_DUTY            25
#define FAN_AUTO_HISTORY_SIZE          32

/*===========================================================================*/
/*                          Internal Types                                    */
/*===========================================================================*/

typedef struct {
    int16_t temp;
    int64_t timestamp_ms;
    bool valid;
} fan_temp_sample_t;

typedef struct {
    bool initialized;
    bool enabled;
    ts_fan_config_t config;
    ts_pwm_handle_t pwm;
    ts_gpio_handle_t tach_gpio;
    ts_fan_mode_t mode;
    uint8_t current_duty;       /* Last successful logical PWM output. */
    bool duty_valid;
    uint8_t target_duty;
    uint16_t rpm;
    int16_t temperature;
    int16_t last_stable_temp;
    uint32_t last_speed_change_time;
    volatile uint32_t tach_count;
    int64_t last_tach_time;
    bool fault;
    int16_t control_temperature;
    int16_t guard_temperature;
    int16_t predicted_temperature;
    float slope_c_per_min;
    float controller_gain;
    float cooling_response;
    ts_fan_auto_state_t auto_state;
    bool guard_active;
    bool temp_stale;
    int64_t guard_release_since_ms;
    int64_t guard_last_observation_ms;
    int64_t guard_last_report_ms;
    ts_temp_source_type_t guard_last_source;
    uint32_t guard_last_identity;
    bool response_observing;
    int64_t response_until_ms;
    float response_slope_before;
    fan_temp_sample_t temp_history[FAN_AUTO_HISTORY_SIZE];
    uint8_t temp_history_next;
    uint8_t temp_history_count;
    int64_t last_auto_update_ms;
    float auto_fall_credit;
} fan_instance_t;

