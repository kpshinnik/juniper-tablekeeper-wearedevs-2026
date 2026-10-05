"""Independent exhaustive oracle for the bounded Stage 4 seating problem.

No product code or official test implementation is imported. Inputs are public API
responses and declared fixture order; the objective is stage-4.md's ordered tuple.
"""
from datetime import datetime


def overlaps(a, b):
    return datetime.fromisoformat(a[0]) < datetime.fromisoformat(b[1]) and datetime.fromisoformat(b[0]) < datetime.fromisoformat(a[1])


def interval(booking):
    return booking['starts_at'], booking['ends_at']


def solve(tables, pairs, reservations, closure, prior_closures=()):
    """Return the exact optimal public assignment, or None when infeasible."""
    options = [(table['id'],) for table in tables] + [tuple(pair) for pair in pairs]
    window = closure['from'], closure['to']
    confirmed = [r for r in reservations if r['status'] == 'confirmed']
    considered = sorted((r for r in confirmed if overlaps(interval(r), window)), key=lambda r: r['reference'])
    fixed = [r for r in confirmed if not overlaps(interval(r), window)]
    closures = [*prior_closures, closure]
    choices = []
    for r in considered:
        valid = []
        for rank, option in enumerate(options):
            capacity = sum(r['accepted_terms']['capacities'][t] for t in option)
            if capacity < r['party_size']:
                continue
            if any(c['table_id'] in option and overlaps(interval(r), (c['from'], c['to'])) for c in closures):
                continue
            if any(set(option).intersection(f['table_ids']) and overlaps(interval(r), interval(f)) for f in fixed):
                continue
            valid.append((rank, option, set(option) != set(r['table_ids']), capacity-r['party_size']))
        choices.append(valid)
    best = None
    selected = None

    def visit(index, assignments, moved, unused, ranks):
        nonlocal best, selected
        if best is not None and (moved > best[0] or (moved == best[0] and unused > best[1])):
            return
        if index == len(considered):
            objective = moved, unused, tuple(ranks)
            if best is None or objective < best:
                best = objective
                selected = list(assignments)
            return
        for rank, option, changed, waste in choices[index]:
            if any(set(option).intersection(previous) and overlaps(interval(considered[index]), interval(considered[j]))
                   for j, previous in enumerate(assignments)):
                continue
            visit(index+1, assignments+[option], moved+int(changed), unused+waste, ranks+[rank])

    visit(0, [], 0, 0, [])
    if selected is None:
        return None
    return {
        'moved_count': best[0], 'unused_seats': best[1], 'rank_vector': list(best[2]),
        'assignments': [{'reference': r['reference'], 'table_ids': list(option), 'changed': set(option) != set(r['table_ids'])}
                        for r, option in zip(considered, selected)],
    }
