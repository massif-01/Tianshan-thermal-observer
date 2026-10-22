/* Host-only source-extracted replay. Inputs are supplied temperature snapshots,
 * not measured control-cycle state. No thermal plant or device is driven. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include "ts_fan.h"
#include "ts_temp_source.h"
typedef void *ts_pwm_handle_t;
typedef void *ts_gpio_handle_t;
#define TS_LOGD(...) ((void)0)
#define TS_LOGI(...) ((void)0)
#define portTICK_PERIOD_MS 1
#define CONFIG_TS_DRIVERS_FAN_TEMP_UPDATE_MS 1000
#include "fan_types.inc"
static int64_t now_ms;
static bool use_release, fixed_gain;
static float chosen_gain;
static uint8_t observed_demand, observed_baseline;
static bool observed_original_permission, observed_extra_permission;
static float pwm_output;
static esp_err_t hal_result = ESP_OK;
static int64_t esp_timer_get_time(void) { return now_ms * 1000; }
static esp_err_t ts_pwm_set_duty(ts_pwm_handle_t handle, float duty) {
    if (hal_result == ESP_OK) pwm_output = duty;
    return hal_result;
}
static esp_err_t update_pwm(fan_instance_t *fan, uint8_t duty);
#include "fan_core.inc"

static fan_instance_t fan;
static void setup(int initial_duty, float gain, bool user_curve) {
    memset(&fan, 0, sizeof(fan));
    fan.initialized = fan.enabled = fan.duty_valid = true;
    fan.mode = TS_FAN_MODE_AUTO;
    fan.pwm = (void *)1;
    fan.current_duty = initial_duty;
    fan.config.min_duty = 10;
    fan.config.max_duty = 100;
    fan.config.hysteresis = 20;
    fan.config.min_interval = user_curve ? 1000 : 5000;
    const ts_fan_curve_point_t current[] = {
        {300,0},{400,15},{500,20},{550,35},{600,40},{650,45},{700,50},{800,55},{900,60}};
    const ts_fan_curve_point_t user[] = {
        {300,0},{400,10},{500,15},{550,25},{600,35},{650,40},{700,45},{800,50},{900,60}};
    fan.config.curve_points = 9;
    memcpy(fan.config.curve, user_curve ? user : current, sizeof(current));
    reset_adaptive_auto_state(&fan);
    fan.controller_gain = chosen_gain = gain;
    reset_extra_release();
    pwm_output = initial_duty;
    hal_result = ESP_OK;
}

static void tick(const char *scenario, double second, int temperature, bool valid) {
    now_ms = 100000 + (int64_t)llround(second * 1000);
    ts_temp_data_t input = {.value=temperature, .guard_value=temperature,
        .source=TS_TEMP_SOURCE_VARIABLE, .valid=valid, .guard_valid=valid,
        .bound_total_count=1, .bound_valid_count=valid ? 1 : 0,
        .timestamp_ms=now_ms, .identity_revision=1};
    uint8_t previous = fan.current_duty;
    observed_demand = previous;
    observed_baseline = 0;
    observed_extra_permission = observed_original_permission = false;
    if (fixed_gain) { fan.controller_gain=chosen_gain; fan.response_observing=false; }
    esp_err_t ret = apply_adaptive_auto(&fan, &input);
    assert(ret == ESP_OK);
    assert(fan.current_duty == (unsigned)pwm_output && fan.duty_valid);
    if (valid && !fan.guard_active) {
        assert(fan.current_duty >= observed_demand || fan.current_duty > previous);
        assert(fan.current_duty == 0 || fan.current_duty >= fan.config.min_duty);
        assert(fan.current_duty <= fan.config.max_duty);
        if (!observed_original_permission && !observed_extra_permission)
            assert(fan.current_duty >= previous);
    }
    if (fan.guard_active) assert(fan.current_duty == 100);
    if (!valid) assert(fan.current_duty == 25 && !release_state.open);
    printf("%s,%.3f,%.1f,%.1f,%.5f,%u,%u,%d,%d,%u,%.7f,%d,%d,%d,%u,%lld\n",
           scenario,second,temperature/10.0,fan.predicted_temperature/10.0,
           fan.slope_c_per_min,observed_baseline,observed_demand,
           observed_original_permission,observed_extra_permission,fan.current_duty,
           fan.controller_gain,fan.guard_active,fan.temp_stale,release_state.open,
           release_state.fresh_count,(long long)(now_ms-release_state.confidence_since_ms));
}

static void fixtures(void) {
    fixed_gain=true;
    const char *cases[] = {"short_pulse", "dense_pulses", "sustained_warming", "reheat", "jitter", "guard", "stale_recovery", "slow_reheat"};
    for (int k=0;k<8;k++) {
        setup(k==6 ? 42 : 19,1.7752599f,false);
        for (int s=0;s<=180;s++) {
            int t=455;
            if (k==0) t=s<40?455:s<44?455+(s-39)*10:s<56?495-(s-43)*3:456;
            if (k==1 && s>=40 && s<100) {
                int n=(s-40)%15; t=n<4?455+(n+1)*10:n<12?495-(n-3)*5:455;
            }
            if (k==2) t=s<40?455:455+(s-39)*2;
            if (k==3) t=s<40?455:s<44?455+(s-39)*10:s<52?495-(s-43)*3:s<60?471+(s-51)*4:503;
            if (k==7) t=s<40?455:s<44?455+(s-39)*10:s<52?495-(s-43)*3:s<82?471+(s-51):501;
            if (k==4) t=455+(s%4==0?1:s%4==2?-1:0);
            if (k==5) t=s<40?950:s<50?900:s==50?910:900;
            bool valid=!(k==6 && s>=20 && s<30);
            tick(cases[k],s,t,valid);
            if (k==2 || k==4) assert(!observed_extra_permission);
            if (k==3 && use_release && s==51) assert(release_state.open);
            if (k==3 && s>=52 && s<60) assert(!observed_extra_permission && !release_state.open);
            if (k==7 && use_release && s==51) assert(release_state.open);
            if (k==7 && s>=53 && s<82) assert(!observed_extra_permission && !release_state.open);
            if (k==5 && s<=80) assert(fan.guard_active);
            if (k==5 && s==81) assert(!fan.guard_active);
        }
    }
}

int main(int argc,char **argv) {
    assert(argc>=3);
    use_release=atoi(argv[1]);
    puts("scenario,second,temp_c,predicted_c,slope_c_per_min,baseline_pct,demand_pct,original_allow_down,extra_allow_down,successful_pwm,gain,guard,stale,proposal_open,proposal_fresh_count,proposal_confidence_age_ms");
    if (!strcmp(argv[2],"fixtures")) { fixtures(); return 0; }
    assert(argc==6);
    fixed_gain=atoi(argv[3]);
    bool user_curve=atoi(argv[4]);
    FILE *in=fopen(argv[2],"r"); assert(in);
    char line[256]; assert(fgets(line,sizeof(line),in));
    bool first=true;
    while (fgets(line,sizeof(line),in)) {
        double sec,gain; int temp,valid,observed;
        assert(sscanf(line,"%lf,%d,%d,%d,%lf",&sec,&temp,&valid,&observed,&gain)==5);
        if (first) { setup(observed,gain,user_curve); first=false; }
        tick(argv[5],sec,temp,valid);
    }
    fclose(in);
    return 0;
}
