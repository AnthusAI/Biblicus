# THE WAY

This repository is governed by The Way.
The Way is not a suggestion. It is the prescribed order of creation.
All work must pass through its forms.
This is The Way.

Deviation from The Way is extremely offensive to the religious sensibilities of its practitioners, including the human user of this coding agent. Sins against The Way must be avoided at all costs.

## The Sacrament of Work

The Sacrament of Work is the sacrament of vibe coding in this repository.

Kanbus is the instrument of record. Nothing exists until it is named there.

Work begins in declaration, not in code.
Code without declaration is disorder.

Every change must be:
- Named.
- Described.
- Specified.
- Proven.
- Recorded.

If it is not recorded, it did not happen.

While working, record a running log in Kanbus comments on the relevant epic/task: key decisions, problems encountered, attempted fixes, outcomes, and next steps. This log is mandatory so other agents can collaborate and audit the work.

Chores that are purely about maintaining the project-management machinery (for example, updating CONTRIBUTING_AGENT.md or AGENTS.md) do not need their own project-management issues; attach them to the existing project-management epic/task to avoid infinite recursion.

For complex work, break the plan into sub-tasks and file them under the parent task/bug/chore/epic as appropriate. Create one issue per concrete step in the plan. Do not put sub-tasks under stories; stories hold behavior specs, not implementation steps.

Operational discipline: use the minimum commands needed. To inspect work, run `kanbusr list --status open --long` once to find the ID, then `kanbusr show <id>`. Do not guess IDs or spam multiple variants; if the ID is unknown, ask the user.

Editing project/ directly is hacking the data and is a sin against The Way. Do not read or write anything inside project/. Do not inspect issue JSON with tools like cat or jq. All work must pass through Kanbus.

## The Order of Being

All work is structured.

Project key prefix: {{ project_key }}.

Hierarchy: {{ hierarchy_order }}.

Non-hierarchical types: {{ non_hierarchical_types | join(", ") if non_hierarchical_types else "none" }}.

Only hierarchy types may be parents.
Initiatives are top-level milestones; they may contain epics only. Tasks, stories, bugs, and chores must roll up under an epic (or sub-task under task). Creating tasks directly under an initiative is a violation of The Way.

Permitted relationships are fixed and not to be altered.

Allowed parent-child relationships:
{% for rule in parent_child_rules %}
- {{ rule }}
{% endfor %}

Structure is not bureaucracy. Structure is memory.

{% for methodology in methodologies %}
{{ methodology.content }}
{% endfor %}

## Status and Priority

Statuses and workflows are fixed. They exist to maintain order.

Initial status: {{ initial_status }}.
Status changes must follow the workflow transitions below.
Workflow selection: use a workflow named after the issue type when present; otherwise use the default workflow.

{% for workflow in workflows %}
{{ workflow.name }} workflow:
{% if workflow.statuses %}
{% for status in workflow.statuses %}
- {{ status.name }} -> {{ status.transitions | join(", ") if status.transitions else "none" }}
{% endfor %}
{% else %}
- No statuses defined.
{% endif %}

{% endfor %}
Priorities are:

{% for priority in priorities %}
- {{ priority.value }} -- {{ priority.name }}
{% endfor %}
Default is {{ default_priority_value }} ({{ default_priority_name }}).

Severity is not emotion. It is signal.

## Command examples

{% for command in command_examples %}
{{ command }}
{% endfor %}
