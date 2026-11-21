# InvenTree Exchange Design

This page details the [InvenTree exchange](../spec.md#inventree-exchange) capability. It builds on
[data interchange](../spec.md#data-interchange), [object identity](../spec.md#object-identity), and
the [part and supply model](../spec.md#part-and-supply-model).

## Counterparts

| Instance ID | Description | Release policy |
| --- | --- | --- |
| `vl-itree` | The owner's InvenTree deployment, maintained in the [vl-itree repository](https://github.com/volod/vl-itree) | Released together with KN on one pinned target InvenTree release, the newest stable release at release time; currently `1.7.3` through the `vl-itree` release `v0.1.0` |

Other instances use the same profile shape, need their own owner approval, and are probed on every
session. Any instance can run a release other than the target.

## Target release

The joint target is set by the `vl-itree` release tag `v0.1.0` (commit `c85fb56`). Its
`docker/versions.env` is the source of the pins below, and `deploy/versions.yaml` in KN copies
them. The KN test service runs the same four images.

| Image | Tag | Digest |
| --- | --- | --- |
| `inventree/inventree` (server and worker) | `1.7.3` | `sha256:bd58a1d1891dac39a19b5c40a7fa6bd9fc4d6752ae0bd69da4582a4afce5dfb7` |
| `postgres` | `17.12` | `sha256:b60e90042aa6b8dbecd58e224b3e36114dbf8ad754465264c2476ad58a86e45c` |
| `redis` | `7.4.12-alpine` | `sha256:7f7d30b7fdd09467bac58198a1f166dd69789d348d4fe859cccb20e0cf287fbe` |
| `caddy` | `2.11.9-alpine` | `sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0` |

The digests are multi-arch index digests. InvenTree `1.7.3` declares API version 570 in its
`api_version.py`, and the probe confirms the value the instance reports.

## The vl-itree deployment

The release `v0.1.0` adapts the official InvenTree 1.7.3 Compose recipe. Facts that affect the
exchange:

- `run-itree.sh` builds the runtime `.env` from `docker/env.template`, the untracked `.env.local`,
  and `docker/versions.env`, validates it, and then calls Docker Compose. `.env.local` cannot
  override the image pins. `INVENTREE_AUTO_UPDATE=True` stays on, so a changed pin migrates the
  database on the next start.
- HTTPS listens on `INVENTREE_BIND_ADDR` (default `127.0.0.1`, port 8443), and plain HTTP binds
  only to `127.0.0.1` (port 8080) and redirects to HTTPS. A non-loopback bind with an `http://`
  site URL is refused. Clients must use the host name of `INVENTREE_SITE_URL`, which the
  certificate covers.
- Certificate mode `internal` uses Caddy's internal CA, whose root `run-itree.sh export-ca`
  exports with its SHA-256 fingerprint. Mode `owner` mounts an owner-supplied certificate and key.
- The launcher refuses a missing, placeholder, well-known default, or shorter than 16-character
  password, unless the loopback-only `--dev` mode is used. `rotate-db-password` changes the
  password of an existing database.
- `run-itree-dump.sh` writes the database dump, a secret `keys.tar.gz` with `secret_key.txt`,
  `config.yaml`, `oidc.pem`, and the internal CA, and the assets. It fails when the secret key or
  `config.yaml` is missing.
- The `Caddyfile` is vendored from InvenTree 1.7.3, and its local changes are marked.
- The repository documents the upgrade, restore, and the `kn-exchange` user and token in `docs/`.
- The running instance moves to `v0.1.0` through the release's one-time migration. Before it, the
  instance ran the floating `stable` tag over plain HTTP on every interface with the default
  database password, so KN does not connect to it until the migration is reported.
- No API user exists by default. The owner creates the `kn-exchange` user and its token.
- KN never reads the InvenTree database directly; it uses only the REST API.

## vl-itree requirements

`vl-itree` can run on another machine, so KN exchange requires the following of it. The owner
applies these changes in the `vl-itree` repository. The last column shows how `v0.1.0` meets
each one.

| Requirement | Rule | In `v0.1.0` |
| --- | --- | --- |
| Pinned release | `inventree/inventree`, `postgres`, `redis`, and `caddy` are referenced by exact tag and digest. The InvenTree tag is the joint target release. The `Caddyfile` is vendored from the same InvenTree tag. | `docker/versions.env`; `docker/Caddyfile` from 1.7.3, checked against the upstream hash by the tests |
| TLS | A non-loopback listener serves HTTPS only. Plain HTTP binds to `127.0.0.1` or only redirects. The certificate is owner-supplied or from the proxy's internal CA, whose root certificate is exported for KN. Clients never disable verification. | Modes `internal` and `owner`; `export-ca`; HTTP on loopback only |
| Bind address | Published ports bind to an address set in `.env`, `127.0.0.1` by default. A non-loopback bind with an `http://` site URL is refused. | `INVENTREE_BIND_ADDR` in `.env.local` |
| Password guard | Secrets live in an untracked local file that the launcher never overwrites. A working instance refuses to start when a password is missing, a placeholder, a known default such as `inventree`, or shorter than 16 characters. Only an explicit loopback-only development mode skips the guard. Existing databases get a scripted password rotation. | `.env.local` (mode 600), checks in `run-itree.sh`, `rotate-db-password`, `--dev` |
| Backups | The dump also holds the secret key and generated configuration files, and no secret appears in its metadata or in logs. | `keys.tar.gz` and `SHA256SUMS`; `metadata.txt` holds no secrets |
| Upgrade procedure | Offline backup, change the pinned tag, start, confirm `version` and `apiVersion` from `GET /api/`, and keep the backup until KN's checks pass. | `docs/upgrade.md` and `docs/backup-restore.md` |
| API user | A dedicated `kn-exchange` user with view-only roles: `part_category`, `part`, and `purchase_order`, plus `stock` and `stock_location` only for the optional availability read. Write roles are added only after write approval. | `docs/kn-api-user.md` creates a `kn-read` group with view-only roles, but lists `purchase_order` as optional |

## API facts the adapter relies on

These facts come from the InvenTree documentation read on 2026-11-21 (`latest`, API version 582)
and from the 1.7.3 source (API version 570). The schema-registry task confirms each one against
the target release's captured snapshot before a profile uses it.

- `GET /api/` returns server information, including the software `version` and the integer
  `apiVersion`. `GET /api/version/` returns `version.server` and `version.api` with commit
  details.
- The OpenAPI schema is generated with drf-spectacular. The probe confirms its download path
  rather than assuming it.
- Token authentication uses the header `Authorization: Token <token>`. A token is issued through
  `GET /api/user/me/token/` with basic authentication and is shown once. Basic authentication can be
  disabled on the server, and it is refused for users with MFA. OAuth2 scoped tokens are also
  available. From 1.6.0, tokens use a v2 format derived from the server secret, so a database
  restore without the matching secret invalidates tokens. A token expires within 365 days. Each
  issuance call with the same token name revokes the previous token, so KN never calls the
  issuance endpoint.
- Permissions in 1.7.3 come from roles. `part` covers parts, manufacturer parts, and supplier
  parts. `purchase_order` covers companies, manufacturer parts, supplier parts, supplier price
  breaks, and purchase orders. `part_category` covers categories. `pricing` covers only cached part
  pricing and sale and internal price breaks. Parameters, parameter templates, and attachments
  have no role of their own.
- List endpoints require the `limit` query parameter, with offset pagination.
- `403` means permission denied and `409` means a locked object. API throttling maps to the
  `rate_limited` error code.
- Parameters are generic: a parameter has `template`, `model_type`, `model_id`, `data`, and
  `data_numeric`. A template has `name`, `units`, `description`, `model_type`, `checkbox`, `choices`,
  `selectionlist`, `enabled`, and `unique`.
- Several resources expose an `updated` field (supplier parts, price breaks, parameters, stock
  items). Where a profile declares one, it becomes an `updated_since` cursor. Otherwise the
  resource is listed in full and compared by record hash.
- `/api/audit/` is a read-only audit log. It can supply an optional change feed.

## Resource mapping

Endpoints are those of the latest documentation. The target-release profile records the confirmed
paths.

| InvenTree resource | Endpoint | KN class and fields | Default owner | Notes |
| --- | --- | --- | --- | --- |
| Company | `/api/company/` | Organization with roles from `is_manufacturer`, `is_supplier`, and `is_customer`; name, description, website, currency, `tax_id` | `kn` for manufacturer and supplier facts; `counterpart` for `is_customer` and `is_internal` | Customer companies are read only as roles, and they are never exported |
| Contact, Address | `/api/company/contact/`, `/api/company/address/` | Not exchanged, apart from a company's country | - | Personal data is excluded |
| ManufacturerPart | `/api/company/part/manufacturer/` | Manufacturer part: legal manufacturer and `MPN`, description, link | `kn` | Identity key; `barcode_hash` is read-only |
| SupplierPart | `/api/company/part/` | Supplier offer: supplier, `SKU`, packaging, `pack_quantity`, availability, `primary`, link | `kn`, except `primary` (`counterpart`) | `primary` marks the owner's preferred supplier |
| SupplierPriceBreak | `/api/company/price-break/` | Price observation: quantity, price, currency, observed time | `kn` | Exported only when the source licence permits redistribution; needs the `purchase_order` role, not `pricing` |
| ParameterTemplate, Parameter | Generic parameter resources | Attribute-dictionary field ID, unit, value, and qualifier, for parts, manufacturer parts, supplier parts, and companies | `kn` for templates KN creates; `counterpart` otherwise | Units must match the attribute dictionary or the value is reported |
| PartCategory | `/api/part/category/` | Concept in a KN classification scheme through an analyst crosswalk | `counterpart` | Category creation is off by default |
| Part | `/api/part/` | The owner's internal part, bound to a product model or manufacturer part; `IPN`, name, units, revision, `active`, `consumable` | `counterpart` | Part creation is off by default |
| Attachment | `/api/attachment/` | Document reference by link and hash | `kn` for links KN adds | Files are uploaded only when the licence permits |
| Tag | `/api/tag/` and `tags` fields | Tag concept | `counterpart` | List filter `tag_name` |
| StockItem, StockLocation | `/api/stock/`, `/api/stock/location/` | Optional read-only aggregate availability per part | `counterpart` | Never written; serials, owners, and customers are excluded |
| Orders, builds, users, notes | Various | Not exchanged | - | Outside the boundary |

The binding location is the model's plugin metadata under a `kn` key when the target release
exposes metadata for that model. In every case the exchange ledger holds the binding.

Values the owner entered in InvenTree carry the `owner_entered` source rank, the highest in the
[update policy](../spec.md#update-policy). They win over manufacturer and distributor data and are
flagged `owner_override` where they differ from first-party values. Values that KN wrote to
InvenTree come back as echoes, not as owner entries, through the exchange ledger. For
counterpart-owned fields, InvenTree is the only source.

## Diff-classifier fixtures

No profile supports releases before the target. These documented InvenTree API changes are the
kinds of change a future release can bring, so each one becomes a schema-diff fixture for the
classifier. API numbers come from the server's `api_version.py` history. Every entry except API
579 is part of the 1.7.3 target. API 579 comes after it, so it is the first known change that the
next upgrade check meets.

| Version | Change | Expected class |
| --- | --- | --- |
| Release 1.2.0 | Part parameter models removed; generic Parameter and ParameterTemplate added | `breaking` for mapped parameter fields |
| API 456 | `default_supplier` removed from Part; `primary` added to SupplierPart | `breaking` (removal) and `compatible` (addition) |
| API 534 | List filter `tags` renamed `tag_name` | `breaking` (filter rename) |
| API 556 | `is_internal` added to Company | `compatible` |
| API 562 | Pricing endpoints moved under `/api/pricing/`; legacy paths return `308`; pricing fields need a role | `breaking` (endpoint move) |
| API 579 | `barcode_hash` became read-only on ManufacturerPart | `breaking` when the field is written |
| Release 1.6.0 | Token v2 format | Authentication change reported by the upgrade check |

## Verification items

The schema-registry task and the first `vl-itree` read run confirm these before the target profile
is reviewed:

- that the instance reports version `1.7.3` and API version 570, and that its image digest
  matches the [target release](#target-release);
- the OpenAPI download path and whether the instance permits schema download;
- the metadata endpoints per model;
- which resources expose `updated` and support filtering on it;
- the role permissions that the `kn-exchange` user needs for reading and for each export profile,
  starting from the roles in the [vl-itree requirements](#vl-itree-requirements);
- whether site-wide MFA enforcement is on, since token issuance follows MFA rules from 1.7.1;
- the HTTPS site URL of `vl-itree`, its certificate mode, and the CA certificate KN must trust,
  with its SHA-256 fingerprint.
