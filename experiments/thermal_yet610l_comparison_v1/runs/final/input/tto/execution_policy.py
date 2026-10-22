"""User-authorized experiment scheduling policy. No control writes or TTL changes."""
POLICY_ID='YET-SYNC-TRANSIENT-TEMP-CONTINUE-v1'
class ExecutionPolicy:
 def __init__(self):
  self.fatal=False;self.reasons=[];self.context=None;self.current_transient=False
 def observe(self,engine):
  fan=engine.fan['data'] if engine.fan else {}
  temp=engine.temp['data'] if engine.temp else {}
  reasons=[]
  for key in ['fault','guard_active']:
   if fan.get(key) is True:reasons.append(key)
  if fan.get('enabled') is False:reasons.append('fan_disabled')
  if fan.get('mode') is not None and fan['mode']!='auto':reasons.append('non_auto')
  if temp.get('manual_mode') is True:reasons.append('manual_temperature')
  if temp.get('active_source') not in (None,'variable','default'):reasons.append('unapproved_active_source')
  # Source variable/default is deliberately separate from protected settings.
  context=(fan.get('mode'),fan.get('enabled'),temp.get('manual_mode'),temp.get('bound_variable'))
  if engine.fan and engine.temp and all(v is not None for v in context[:3]):
   if self.context is not None and context!=self.context:reasons.append('protected_control_context_changed')
   self.context=context
  self.current_transient=bool(fan.get('temp_stale') is True or temp.get('normalized_valid') is False or temp.get('active_source')=='default')
  if reasons:self.fatal=True;self.reasons=list(dict.fromkeys(self.reasons+reasons))
