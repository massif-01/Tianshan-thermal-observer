from pathlib import Path
import difflib
R=Path(__file__).resolve().parents[1];f=R/'work/runtime-024/tto/collector.py';old=(R/'sources/candidate-wheel/tto/collector.py').read_text();s=old
needle="            trace.on_request_redirect.append(reject_redirect)"
s=s.replace(needle,needle+'''
            # Only endpoint polls opt in. Never retain headers, URLs or payloads.
            def phase_callback(phase):
                async def record_phase(session, context, params):
                    diagnostics = (context.trace_request_ctx or {}).get('poll_diagnostics')
                    if diagnostics is not None:
                        diagnostics['last_phase'] = phase
                        diagnostics['events'].append({'phase': phase, 'mono_s': time.monotonic()})
                return record_phase
            for signal_name, phase in (
                ('on_request_start', 'request_start'),
                ('on_connection_queued_start', 'connector_queue'),
                ('on_connection_queued_end', 'connector_acquired'),
                ('on_dns_resolvehost_start', 'dns'),
                ('on_connection_create_start', 'connect'),
                ('on_connection_create_end', 'connection_ready'),
                ('on_connection_reuseconn', 'connection_reused'),
                ('on_request_headers_sent', 'request_headers_sent'),
                ('on_request_end', 'response_headers_received')):
                getattr(trace, signal_name).append(phase_callback(phase))''')
s=s.replace("                        try:\n                            async with session.get(c['base_url'].rstrip('/') + paths[key], headers=h, allow_redirects=False) as response:","""                        diagnostics = {'last_phase': 'before_request', 'events': []}
                        try:
                            async with session.get(c['base_url'].rstrip('/') + paths[key], headers=h, allow_redirects=False,
                                                   trace_request_ctx={'poll_diagnostics': diagnostics}) as response:
                                diagnostics['last_phase'] = 'response_body'""")
s=s.replace("                                payload = json.loads(raw)", "                                diagnostics['response_bytes'] = len(raw)\n                                payload = json.loads(raw)\n                                diagnostics['last_phase'] = 'complete'")
s=s.replace("received_mono_s=received, round_trip_ms=(received-sent)*1000)", "received_mono_s=received, round_trip_ms=(received-sent)*1000,\n                                    poll_diagnostics=diagnostics)")
s=s.replace("sent_mono_s=sent, cancelled_mono_s=time.monotonic())", "sent_mono_s=sent, cancelled_mono_s=time.monotonic(), poll_diagnostics=diagnostics)")
s=s.replace("                                error_class=type(e).__name__)","                                error_class=type(e).__name__, poll_diagnostics=diagnostics)")
assert s!=old
f.write_text(s);(R/'deliverables/collector-diagnostics.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/tto/collector.py',tofile='b/tto/collector.py')))
