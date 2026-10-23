"""Bounded projection of committed ledger rows; no forecasting or source access."""
import copy
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from .web_encoding import short

WINDOW = 3600
STRIDE = 5
PAGE = 128


def utc_offset(stamp, seconds):
    return (datetime.fromisoformat(stamp.replace('Z', '+00:00')) + timedelta(seconds=seconds)).isoformat()


class PredictionView:
    def __init__(self, origin):
        self.origin = origin
        self.rows = OrderedDict()
        self.cursor = 0
        self.context = None
        self.failure = None
        self.barrier = -float('inf')
        self.lock = threading.Lock()

    def committed(self, stream, row):
        # This is the single boundary between the formal ledger and its optional
        # read projection. A failed projection stays unavailable until a new run.
        if self.failure:return
        try:
            if stream=='context':self.update(*row)
            else:self.apply(stream,row)
        except Exception as exc:
            with self.lock:self.failure=type(exc).__name__

    def apply(self, stream, row):
        if stream not in ('predictions', 'scores') or row['method'] != 'G2-HOLD':
            return
        with self.lock:
            if stream == 'predictions':
                issued = row['issued_at']
                value = dict(prediction_id=row['prediction_id'], run_id=short(row['run_id']), ledger_run_id=row['run_id'],
                    source_epoch=row['source_epoch'], model_id=row['model_sha256'], backend_model_id=row['model_id'],
                    spec_id=row['spec_sha256'], scenario='HOLD', horizon_s=row['horizon_s'],
                    origin_elapsed_ms=(row['observed_through_mono_s']-self.origin)*1000,
                    issued_elapsed_ms=(issued['mono_s']-self.origin)*1000,
                    target_elapsed_ms=(row['target_mono_s']-self.origin)*1000,
                    input_cutoff_elapsed_ms=(row['observed_through_mono_s']-self.origin)*1000,
                    origin_at_utc=utc_offset(issued['utc'], row['observed_through_mono_s']-issued['mono_s']),
                    issued_at_utc=issued['utc'], target_at_utc=utc_offset(issued['utc'], row['target_mono_s']-issued['mono_s']),
                    value_C=row['value_C'], phase_at_origin=row['origin_state_status'],
                    evidence_mode='issued_online' if row['publication_mode']=='live' else 'test_replay',
                    status='late_publication' if row['late'] else 'pending' if row['value_C'] is not None else 'unavailable',
                    reason_code=row['reason'], conditional_assumptions=None if row['conditional_assumptions']==[] else copy.deepcopy(row['conditional_assumptions']),observed_C=None, error_C=None)
                self.rows[row['prediction_id']] = value
            else:
                value = self.rows.get(row['prediction_id'])
                if value is None:  # Its origin has left the retained window.
                    return
                if row['status']=='scored':
                    value.update(status='matched', observed_C=row['label_value_C'], error_C=row['error_C'],
                        label=dict(label_elapsed_ms=(row['label_received_mono_s']-self.origin)*1000, source_ref=row['label_ref'],received_at_utc=row['label_received_utc']))
                else:
                    reason=row['reason']
                    value.update(status='missing_label' if reason=='missing_qualified_label_within_2s' else 'not_comparable', reason_code=reason)
                value['settled_elapsed_ms'] = (row['settled_mono_s']-self.origin)*1000
            self.cursor += 1
            value['revision'] = self.cursor

    def update(self, frame, state, deadline):
        with self.lock:
            t=frame['t']
            valid=frame['_communication']['measurement']['TJ_and_rails']['raw_valid'] and state['observer']['phase'] in ('tracking','degraded')
            if not valid or frame['source_reset']:
                self.barrier=t
            self.context=dict(run_id=short(frame['identity']['run_id']), source_epoch=frame['identity']['source_epoch'],
                              model_id=frame['identity']['model_sha256'], spec_id=frame['identity']['spec_sha256'],
                              phase=state['observer']['phase'], input_mono_s=t, deadline=deadline, valid=valid)
            self._trim(t)

    def _trim(self, now):
        cutoff=(now-self.origin-WINDOW)*1000
        while self.rows and next(iter(self.rows.values()))['origin_elapsed_ms'] < cutoff:
            self.rows.popitem(last=False)

    def page(self, since=0, *, now=None, ended=False):
        now=time.monotonic() if now is None else now
        with self.lock:
            self._trim(now)
            eligible=[] if self.failure else [v for v in self.rows.values() if v['revision']>since]
            eligible.sort(key=lambda v:v['revision'])
            page=eligible[:PAGE]
            context=self.context
            latest=[]
            if context and not self.failure:
                latest=[v for v in self.rows.values() if all(v[k]==context[k] for k in ('run_id','source_epoch','model_id','spec_id'))
                        and v['phase_at_origin'] in ('tracking','degraded')]
            batch=[v for v in latest if v['origin_elapsed_ms']==latest[-1]['origin_elapsed_ms']] if latest else []
            until=min(context['deadline'], self.origin+batch[-1]['origin_elapsed_ms']/1000+STRIDE+2.5) if batch else now
            available=bool(not self.failure and not ended and context and context['valid'] and len(batch)==3 and now<until
                           and all(v['status']=='pending' and v['value_C'] is not None
                                   and self.barrier<self.origin+v['origin_elapsed_ms']/1000<=context['input_mono_s'] for v in batch))
            status='available' if available else 'initializing' if context and context['phase']=='provisional' and now<context['deadline'] and not ended and not self.failure else 'unavailable'
            # Realtime identity belongs to the last source frame, including a
            # stop boundary. Terminal history belongs to an actual issued group.
            history=context
            if ended:
                history=next((v for v in reversed(self.rows.values())
                              if v['phase_at_origin'] in ('tracking','degraded')), context)
            return dict(schema='TTO-PREDICTION-PAGE-v1', origin_mono_s=self.origin, ended=ended,
                sync_status='unavailable' if self.failure else 'synced',
                history_identity={k:history[k] for k in ('run_id','source_epoch','model_id','spec_id')} if history else None,
                identity={k:context[k] for k in ('run_id','source_epoch','model_id','spec_id')} if context else None, cursor=since if self.failure else page[-1]['revision'] if page else self.cursor,
                watermark=self.cursor, has_more=not self.failure and len(eligible)>PAGE, retained_from_mono_s=now-WINDOW,
                records=[] if self.failure else copy.deepcopy(page), forecast=dict(provider='observe-ledger',status=status,stride_s=STRIDE,
                    history_window_ms=WINDOW*1000, remaining_valid_ms=max(0.,(until-now)*1000) if available else 0.,
                    latest_prediction_ids=[v['prediction_id'] for v in batch] if available else [],
                    consumable_until_mono_s=until if available else now))

    def final(self, now):
        # One protocol terminal snapshot, not an alternative recorder.
        result=self.page(self.cursor, now=now, ended=True)
        with self.lock:
            result.update(records=[] if self.failure else copy.deepcopy(list(self.rows.values())), cursor=self.cursor, watermark=self.cursor, has_more=False, ended_at_mono_s=now)
        return result
