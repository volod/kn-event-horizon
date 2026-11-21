# InvenTree Exchange Design

This page details the [InvenTree exchange](../spec.md#inventree-exchange) capability. It builds on
[data interchange](../spec.md#data-interchange), [object identity](../spec.md#object-identity), and
the [part and supply model](../spec.md#part-and-supply-model).

## Counterparts

| Instance ID | Description | Release policy |
| --- | --- | --- |
| `vl-itree` | The owner's InvenTree deployment, maintained in the [vl-itree repository](https://github.com/volod/vl-itree) | Released together with KN on one pinned target InvenTree release, the newest stable release at release time |

Other instances use the same profile shape, need their own owner approval, and are probed on every
session. Any instance can run a release other than the target.

## The vl-itree deployment

The repository was read at its initial commit (`4775dcd`). It holds the standard InvenTree
production Compose recipe and three files of its own:

- `docker/docker-compose.yml` runs `postgres:17`, `redis:7-alpine`,
  `inventree/inventree:${INVENTREE_TAG}` as the server and as the worker, and `caddy:alpine` as
  the proxy. There are no plugins and no custom code.
- `run-itree.sh` writes `.env` from an embedded template and provisions `inventree-volume/`. It
  loads or caches images under `docker-images/` and starts the stack. The proxy publishes HTTP on
  host port 8080 and HTTPS on 8443.
- `run-itree-dump.sh` writes a `pg_dump` custom-format database dump, an archive of media, static,
  and config files, and a metadata file under `inventree-dump/<timestamp>/`.

Facts that affect the exchange:

- `INVENTREE_TAG=stable` with `INVENTREE_AUTO_UPDATE=True` lets the InvenTree release float. A
  newly pulled `stable` image migrates the database on start.
- The template sets `INVENTREE_SITE_URL=http://localhost`, serves plain HTTP, and publishes its
  ports on every host interface.
- `run-itree.sh` rewrites `.env` from the embedded template on every start and deletes it on stop.
  A changed password therefore cannot persist, and the template's fixed default database password
  is always the one in use.
- The proxy `Caddyfile` is copied from an untracked `InvenTree/` source checkout, so its version can
  differ from the image.
- The dump covers the database, media, static, and the `config/` directory. It may miss files that
  InvenTree keeps in the data directory, such as the secret key, which API tokens depend on from
  1.6.0.
- No API user exists by default. The owner creates the `kn-exchange` user and its token.
- KN never reads the InvenTree database directly; it uses only the REST API.

## vl-itree requirements

`vl-itree` can run on another machine, so KN exchange requires the following of it. The
[upgrade prompt](vl-itree-upgrade-prompt.md) prepares these changes in the `vl-itree` repository.

| Requirement | Rule |
| --- | --- |
| Pinned release | `inventree/inventree`, `postgres`, `redis`, and `caddy` are referenced by exact tag and digest. The InvenTree tag is the joint target release. The `Caddyfile` is vendored from the same InvenTree tag. |
| TLS | A non-loopback listener serves HTTPS only. Plain HTTP binds to `127.0.0.1` or only redirects. The certificate is owner-supplied or from the proxy's internal CA, whose root certificate is exported for KN. Clients never disable verification. |
| Bind address | Published ports bind to an address set in `.env`, `127.0.0.1` by default. A non-loopback bind with an `http://` site URL is refused. |
| Password guard | Secrets live in an untracked local file that the launcher never overwrites. A working instance refuses to start when a password is missing, a placeholder, a known default such as `inventree`, or shorter than 16 characters. Only an explicit loopback-only development mode skips the guard. Existing databases get a scripted password rotation. |
| Backups | The dump also holds the secret key and generated configuration files, and no secret appears in its metadata or in logs. |
| Upgrade procedure | Offline backup, change the pinned tag, start, confirm `version` and `apiVersion` from `GET /api/`, and keep the backup until KN's checks pass. |
| API user | A dedicated `kn-exchange` user with read-only roles. Write roles are added only after write approval. |

## API facts the adapter relies on

These facts come from the InvenTree documentation read on 2026-11-21 (`latest`, API version 582).
The schema-registry task confirms each one against the target release's captured snapshot before
a profile uses it.

- `GET /api/` returns server information, including the software `version` and the integer
  `apiVersion`. `GET /api/version/` returns `version.server` and `version.api` with commit
  details.
- The OpenAPI schema is generated with drf-spectacular. The probe confirms its download path
  rather than assuming it.
- Token authentication uses the header `Authorization: Token <token>`. A token is issued through
  `GET /api/user/me/token/` with basic authentication and is shown once. Basic authentication can be
  disabled on the server, and it is refused for users with MFA. OAuth2 scoped tokens are also
  available. From 1.6.0, tokens use a v2 format derived from the server secret, so a database
  restore without the matching secret invalidates tokens.
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
| SupplierPriceBreak | `/api/company/price-break/` | Price observation: quantity, price, currency, observed time | `kn` | Exported only when the source licence permits redistribution; the pricing role may be required |
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
classifier. API numbers come from the server's `api_version.py` history.

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

- the target release tag, its digest, and its API version;
- the OpenAPI download path and whether the instance permits schema download;
- the metadata endpoints per model;
- which resources expose `updated` and support filtering on it;
- the role permissions that the `kn-exchange` user needs for reading and for each export profile;
- the HTTPS URL of `vl-itree`, its certificate mode, and the CA certificate KN must trust.
