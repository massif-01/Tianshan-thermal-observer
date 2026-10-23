"""Time mapping from declared clocks and independent anchors only, never temperatures."""
import datetime as dt
import math
from zoneinfo import ZoneInfo


def iso(seconds):
    return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat()


def coordinate(raw, timezone=None):
    """Naive camera time is a coordinate, NOT implicitly host UTC/local time."""
    if isinstance(raw,str):
        try:raw=float(raw)
        except ValueError:pass
    if isinstance(raw, (float,int)):
        value=float(raw)
        if not math.isfinite(value):raise ValueError('Non-finite clock coordinate')
        return value, 'numeric_clock'
    value=dt.datetime.fromisoformat(str(raw).replace('Z','+00:00'))
    if value.tzinfo is None:
        if timezone:
            if timezone.startswith(('+','-')):
                sign=-1 if timezone[0]=='-' else 1
                h,m=map(int,timezone[1:].split(':'))
                tz=dt.timezone(sign*dt.timedelta(hours=h,minutes=m))
            else:tz=ZoneInfo(timezone)
            value=value.replace(tzinfo=tz)
            return value.timestamp(),'declared_timezone'
        return value.replace(tzinfo=dt.timezone.utc).timestamp(),'naive_coordinate_not_utc'
    return value.timestamp(),'timezone_explicit'


def utc_seconds(raw):
    seconds,kind=coordinate(raw)
    if kind!='timezone_explicit':raise ValueError('UTC timestamp must include timezone')
    return seconds


def nonnegative(value, name):
    if value is None or value=='':return None
    value=float(value)
    if not math.isfinite(value) or value<0:raise ValueError(name+' must be finite and >=0, or null')
    return value


def clock_map(profile, run_id, run_clock_pair=None):
    """Return evidence-based affine mapping plus uncertainty; no fitted curve shifts."""
    domain=profile.get('clock_domain')
    anchors=profile.get('sync_anchors',[])
    basis=profile.get('sync_basis')
    if domain=='run_utc' and basis:
        return dict(status='declared_same_run_utc',scale=1.,offset=0.,anchor_error_s=nonnegative(
            profile.get('sync_uncertainty_s'),'sync uncertainty'),flags=[],domain=domain)
    if domain=='run_monotonic' and basis and run_clock_pair:
        if run_clock_pair['run_id']!=run_id:raise ValueError('Monotonic clock pair belongs to another run')
        return dict(status='declared_same_run_monotonic',scale=1.,
            offset=run_clock_pair['utc_s']-run_clock_pair['mono_s'],
            anchor_error_s=nonnegative(profile.get('sync_uncertainty_s'),'sync uncertainty'),flags=[],domain=domain)
    if not domain or not anchors:
        return dict(status='unaligned_clock',scale=None,offset=None,anchor_error_s=None,
                    flags=['clock_domain_or_independent_anchors_missing'],domain=domain)
    pairs=[];kinds=[]
    for anchor in anchors:
        if not anchor.get('evidence'):raise ValueError('Clock anchor needs independent evidence, not temperature correlation')
        s,kind=coordinate(anchor['clock_time'],profile.get('timezone'))
        pairs.append((s,utc_seconds(anchor['run_utc']),nonnegative(anchor.get('uncertainty_s'),'anchor uncertainty')))
        kinds.append(kind)
    if len(set(kinds))!=1:raise ValueError('Clock anchors mix incompatible coordinates')
    pairs.sort()
    if len(pairs)==1:
        scale=1.;offset=pairs[0][1]-pairs[0][0];flags=['single_anchor_offset_only_drift_unverified']
    else:
        if pairs[-1][0]<=pairs[0][0] or pairs[-1][1]<=pairs[0][1]:raise ValueError('Clock anchors must advance')
        scale=(pairs[-1][1]-pairs[0][1])/(pairs[-1][0]-pairs[0][0])
        offset=pairs[0][1]-scale*pairs[0][0];flags=['clock_drift_from_independent_first_last_anchors']
    residual=max(abs(t-(scale*s+offset)) for s,t,_ in pairs)
    bound=None if any(e is None for _,_,e in pairs) else max(e for _,_,e in pairs)+residual
    return dict(status='offset_anchor' if len(pairs)==1 else 'affine_clock_anchors',scale=scale,offset=offset,
                anchor_error_s=bound,residual_max_s=residual,drift_ppm=(scale-1)*1e6,
                anchor_span=[pairs[0][0],pairs[-1][0]],anchor_coordinate_kind=kinds[0],flags=flags,domain=domain)


def align_time(record, session, run_clock_pair=None):
    profile=session.get('time',{})
    mapping=clock_map(profile,record['run_id'],run_clock_pair)
    if record.get('clock_domain')!=profile.get('clock_domain'):
        return dict(status='measurement_clock_not_session_clock',interval_utc_s=None,mapping=mapping,
                    flags=['operator_host_capture_needs_its_own_clock_evidence'])
    actual=record.get('measured_at_raw')
    interval=record.get('measured_interval_raw') or {}
    if actual is None and not interval.get('start'):
        return dict(status='measurement_time_unknown',interval_utc_s=None,mapping=mapping,
                    flags=['mark_import_chat_and_mtime_are_not_measurement_time'])
    raw=[actual,actual] if actual is not None else [interval.get('start'),interval.get('end')]
    if any(x is None for x in raw):raise ValueError('Measurement interval needs both endpoints')
    coords=[coordinate(x,profile.get('timezone')) for x in raw]
    if coords[0][1]!=coords[1][1]:raise ValueError('Measurement interval mixes clock kinds')
    if coords[1][0]<coords[0][0]:raise ValueError('Reversed measurement interval')
    flags=list(mapping['flags'])
    anchor_kind=mapping.get('anchor_coordinate_kind')
    if anchor_kind and (anchor_kind=='numeric_clock')!=(coords[0][1]=='numeric_clock'):
        return dict(status='sample_clock_coordinate_not_anchor_clock',interval_utc_s=None,mapping=mapping,
                    flags=flags+['numeric_elapsed_and_calendar_timestamp_cannot_share_anchor_mapping'])
    if coords[0][1]=='naive_coordinate_not_utc':flags.append('timezone_unknown')
    if mapping['scale'] is None:
        return dict(status='unaligned_clock',interval_utc_s=None,raw_coordinates=[c[0] for c in coords],
                    mapping=mapping,flags=flags)
    if mapping['domain']=='run_utc' and coords[0][1]=='naive_coordinate_not_utc':
        return dict(status='timezone_unknown',interval_utc_s=None,mapping=mapping,flags=flags)
    centers=[mapping['scale']*c[0]+mapping['offset'] for c in coords]
    uncertainty=nonnegative(record.get('time_uncertainty_s'),'measurement uncertainty')
    if uncertainty is None or mapping['anchor_error_s'] is None:
        return dict(status='aligned_center_uncertainty_unknown',interval_utc_s=None,
                    center_interval_utc_s=centers,mapping=mapping,flags=flags+['time_precision_unknown_not_zero'])
    error=abs(mapping['scale'])*uncertainty+mapping['anchor_error_s']
    if len(profile.get('sync_anchors',[]))>=2:
        lo,hi=mapping['anchor_span']
        if coords[0][0]<lo or coords[1][0]>hi:
            return dict(status='outside_clock_anchor_span',interval_utc_s=None,center_interval_utc_s=centers,
                        mapping=mapping,flags=flags+['clock_extrapolation_uncertainty_unbounded'])
    return dict(status='bounded_time',interval_utc_s=[centers[0]-error,centers[1]+error],
                center_interval_utc_s=centers,time_error_s=error,mapping=mapping,flags=flags)
