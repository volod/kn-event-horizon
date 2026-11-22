"""Proposal-specific vocabulary recipes; no network lookups or inferred crosswalks."""

from kn.semantic.proposals import Proposal
from kn.semantic.seed_model import SeedBuilder, native_code, required_text

# Namespace, code column, label column, parent column, scheme origin.
RECIPES = {
    ("space", "04_nasa_tx_tags"): ("nasa_tx_2024", "code", "technology_area", None, "official"),
    ("space", "06_euspa_app_tags"): (
        "euspa_2026",
        "application_tag",
        "application_tag",
        None,
        "official",
    ),
    ("space", "07_service_types"): (
        "services",
        "service_code",
        "service_type",
        None,
        "service_extension",
    ),
    ("microelectronics", "03_product_classifier"): (
        "product_v1",
        "kb_node",
        "class",
        "parent",
        "kb_normalized",
    ),
    ("microelectronics", "04_ecs_technology"): (
        "ecs_sria_2026",
        "tag",
        "technology_domain",
        None,
        "official",
    ),
    ("microelectronics", "05_technology_tags"): (
        "technology",
        "tag_id",
        "technology",
        None,
        "kb_extension",
    ),
    ("microelectronics", "06_application_tags"): (
        "applications",
        "id",
        "application",
        None,
        "kb_normalized",
    ),
    ("microelectronics", "07_service_vocabulary"): (
        "services",
        "id",
        "service",
        None,
        "service_extension",
    ),
    ("gdelt", "03_cameo_classifier"): (
        "cameo_v2",
        "code",
        "action_label",
        "parent_code",
        "official",
    ),
    ("gdelt", "05_gkg_theme_tags"): (
        "gkg_themes_2021",
        "native_theme_code",
        "native_theme_code",
        None,
        "official",
    ),
    ("gdelt", "07_technology_tags"): (
        "technology",
        "tag_id",
        "label",
        "parent_blank_root",
        "kb_extension",
    ),
    ("gdelt", "08_application_tags"): ("applications", "tag_id", "label", None, "kb_extension"),
    ("gdelt", "09_service_vocabulary"): (
        "services",
        "service_id",
        "service",
        None,
        "service_extension",
    ),
}


def import_concepts(builder: SeedBuilder, row: Proposal) -> list[str]:
    if row.domain == "space" and row.sheet == "03_esa_gpt_classifier":
        return _gpt(builder, row)
    if row.domain == "space" and row.sheet == "05_esa_tech_tags":
        return _esa_technology(builder, row)
    recipe = RECIPES.get((row.domain, row.sheet))
    if recipe is None:
        return []
    namespace, code_key, label_key, parent_key, origin = recipe
    values = row.values
    # The OECD proposal assigns local identifiers and includes engineering extensions.
    # One normalized tree retains primary parents without claiming official extensions.
    row_origin = str(values.get("node_status", values.get("origin", origin))).lower()
    code = required_text(values, code_key)
    if code_key == "application_tag":
        code = native_code(code)
    label = required_text(values, label_key)
    if namespace == "product_v1" and label == "Others":
        label += " (" + code + ")"
    identifier = builder.concept(
        namespace,
        code,
        label,
        row,
        origin=row_origin,
        scheme_origin=origin,
        parent=values.get(parent_key) if parent_key else None,
    )
    return [identifier]


def _gpt(builder: SeedBuilder, row: Proposal) -> list[str]:
    values = row.values
    namespace = "esa_gpt_1_1"
    segment = values["gpt_segment_code"]
    parent_id = builder.domain + "." + namespace + "." + segment
    if parent_id not in builder.lineage:
        builder.concept(
            namespace,
            segment,
            values["gpt_segment"],
            row,
            origin="kb_normalized",
            scheme_origin="kb_normalized",
        )
    identifier = builder.concept(
        namespace,
        values["node_code"],
        values["gpt_segment"] + ": " + values["product_category"],
        row,
        origin=values["node_status"].lower(),
        scheme_origin="kb_normalized",
        parent=values.get("parent_node") or segment,
    )
    return [parent_id, identifier]


def _esa_technology(builder: SeedBuilder, row: Proposal) -> list[str]:
    values = row.values
    namespace = "esa_tt_4_1"
    domain = values["td_code"]
    parent_id = builder.domain + "." + namespace + "." + domain
    if parent_id not in builder.lineage:
        builder.concept(namespace, domain, values["technology_domain"], row, origin="official")
    if not values["ts_code"] or not values["technology_subdomain"]:
        return [parent_id]
    code = domain + "." + str(values["ts_code"])
    # Repeated subdomain names are qualified by their technology domain.
    label = values["technology_domain"] + ": " + values["technology_subdomain"]
    return [
        parent_id,
        builder.concept(namespace, code, label, row, origin="official", parent=domain),
    ]
