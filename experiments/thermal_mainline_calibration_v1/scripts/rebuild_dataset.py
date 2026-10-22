"""Recreate the normalized L/M/S example from exact accepted, sealed evidence members."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tool/legacy'))
from tool.util import read, write, sha, legacy_identity
from data_views import index_evidence, strict_segments, make_examples


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True, help='Original accepted R2 evidence archive; never overwritten')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    registration = read(ROOT/'inputs/source-registration.json')
    if sha(a.archive) != registration['original_archive_sha256']:
        raise ValueError('not the accepted source archive')
    legacy_identity()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    roles = read(ROOT/'config/data-roles.json')
    segments, examples, coverage = [], [], {}
    with zipfile.ZipFile(a.archive) as z:
        for role in roles:
            name = role['run']
            source = registration['evidence_sources'][name]
            raw = z.read(source['archive_member'])
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ValueError('evidence member SHA mismatch: '+name)
            evidence = index_evidence(json.loads(raw))
            if evidence['run_id'] != role['run_id']:
                raise ValueError('actual run identity differs')
            strict, cov = strict_segments(evidence)
            ex = make_examples(evidence, strict)
            coverage[name] = cov
            for segment in strict:
                rows = []
                for row in segment['rows']:
                    keep = {k:row[k] for k in ['run','ref','t','mono_s','utc','wall','macro','phase','regime','duration','timeline_index']}
                    keep['values'] = {k:row['values'][k] for k in ['tj','vdd_gpu','vdd_cpu_soc_mss','duty']}
                    rows.append(keep)
                segments.append({**{k:segment[k] for k in ['id','run','source_segment','span_s','eligible_for_fit']},
                                 'rows':rows, 'timeline':[{k:n[k] for k in ['t','inputs']} for n in segment['timeline']]})
            examples.extend({k:v for k,v in row.items() if k not in ['R_TJ','R_IO']} for row in ex)
    data = dict(schema='TTO-G2-MODELING-DATA-v1', units=dict(TJ='C',independent_rails='W',PWM='percent in rows; fraction in timeline'),
                runs=roles, segments=segments, examples=examples, all_seen_development=True)
    (out/'dataset.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    write(out/'coverage.json',coverage)
    expected = registration['normalized_dataset_sha256']
    write(out/'rebuild-result.json',dict(expected_sha256=expected, actual_sha256=sha(out/'dataset.json'),
                                       matches=sha(out/'dataset.json')==expected, raw_sources_modified=False))
    if sha(out/'dataset.json') != expected:
        raise ValueError('normalized dataset differs; preserve new output for diagnosis')
    print('Rebuilt accepted source dataset byte-for-byte:', expected)


if __name__ == '__main__':
    main()
