from collections import defaultdict
from string import Template
from typing import Dict, Optional

from robusta.api import ActionParams, ExecutionBaseEvent, Finding, FindingSeverity, action


def _get_templating_labels(event: ExecutionBaseEvent) -> Dict:
    subject = event.get_subject()
    labels: Dict[str, str] = defaultdict(lambda: "<missing>")
    labels.update(
        {
            "name": subject.name,
            "kind": subject.subject_type.value,
            "namespace": subject.namespace if subject.namespace else "<missing>",
            "node": subject.node if subject.node else "<missing>",
        }
    )
    return labels


class FindingOverrides(ActionParams):
    """
    :var title: Overriding finding title. Title can be templated with name/namespace/kind/node of the resource, if applicable
    :var description: Overriding finding description. Description can be templated with name/namespace/kind/node of the resource, if applicable
    :var severity: Overriding finding severity. Allowed values: DEBUG, INFO, LOW, MEDIUM, HIGH
    :example severity: DEBUG
    :example title: Resource $kind/$namespace/$name is in trouble
    """

    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None


@action
def customise_finding(event: ExecutionBaseEvent, params: FindingOverrides):
    """
    Modify an existing notification message generated by a previous playbook action.
    This lets you modify messages created by other actions without needing to rewrite those actions.

    This action does not create a new Finding, it just overrides the attributes of an existing Finding.
    It must be placed as the last action in the playbook configuration, to override the attributes created by previous
    actions
    """
    severity: Optional[FindingSeverity] = FindingSeverity[params.severity] if params.severity else None

    labels = _get_templating_labels(event)

    title = Template(params.title).safe_substitute(labels) if params.title else None
    description = Template(params.description).safe_substitute(labels) if params.description else None

    event.override_finding_attributes(title, description, severity)


class FindingFields(ActionParams):
    """
    :var title: Finding title. Title can be templated with name/namespace/kind/node of the resource, if applicable
    :var aggregation_key: Aggregation Keys are used for grouping similar types of notifications together.
        |
        For example, all CrashLoopBackOff notifications should have the same Aggregation Key so that Sinks can group them together.
        |
        Generally, each instance of create_finding in your playbooks should specify a unique Aggregation Key, like "Crashing Pod" or "OOMKill".
        |
        Aggregation Keys should generally not include Pod names or other strings that change. If you include dynamic data in the Aggregation Key, each unique Aggregation Key will create it’s own grouping.
    :var description: Finding description. Description can be templated
    :var severity: Finding severity. Allowed values: DEBUG, INFO, LOW, MEDIUM, HIGH

    :example title: "Job $name on namespace $namespace failed"
    :example aggregation_key: "Job Failure"
    :example severity: DEBUG
    """

    title: str
    aggregation_key: str
    description: Optional[str] = None
    severity: Optional[str] = "HIGH"


@action
def create_finding(event: ExecutionBaseEvent, params: FindingFields):
    """
    Create a new notification message. This is the primary way that custom playbooks generate messages.
    """
    labels = _get_templating_labels(event)

    event.add_finding(
        Finding(
            title=Template(params.title).safe_substitute(labels),
            description=Template(params.description).safe_substitute(labels) if params.description else None,
            aggregation_key=params.aggregation_key,
            severity=FindingSeverity.from_severity(params.severity),
            subject=event.get_subject(),
            source=event.get_source(),
        )
    )
