# TV3 Image Management Spec (Draft)

2026-11-10

TV3 stores up to 5 images per product as BYTEA, validated by content and safe under concurrent edits. All values are proposals until marked Agreed.

## Dependencies

| From | TV3 needs |
| --- | --- |
| TV1 | Current `vendor_id` per request, CSRF, frontend stack |
| TV2 | `product` table, `product.version`, `lock_product_for_vendor()` |
| TV4 | Uses TV3's `get_image_data()`; ETag = SHA-256 |

Until these land, TV3 tests against a stub `product(id, vendor_id, status, version)`.

## Decisions

| Decision | Proposed | Status |
| --- | --- | --- |
| Formats | JPEG, PNG, WebP | Proposed |
| Max size | 5 MB | Proposed |
| Max images | 5 per product | Proposed |
| Duplicate file | 409 | Proposed |
| Delete | Hard delete | Proposed |
| Primary | One per product; first upload | Proposed |
| Version token | `If-Match: "<product.version>"`; every image write bumps it | Proposed |
| Public ETag | SHA-256 hex | Proposed |

## Data model

```sql
CREATE TABLE product_image (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id   BIGINT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  content_type TEXT NOT NULL CHECK (content_type IN ('image/jpeg','image/png','image/webp')),
  size_bytes   INTEGER NOT NULL CHECK (size_bytes BETWEEN 1 AND 5242880),
  sha256       CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  data         BYTEA NOT NULL,
  position     SMALLINT NOT NULL CHECK (position BETWEEN 0 AND 4),
  is_primary   BOOLEAN NOT NULL DEFAULT false,
  alt_text     TEXT CHECK (char_length(alt_text) <= 255),
  version      INTEGER NOT NULL DEFAULT 1,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (octet_length(data) = size_bytes),
  UNIQUE (product_id, position) DEFERRABLE INITIALLY DEFERRED,
  UNIQUE (product_id, sha256)
);
CREATE UNIQUE INDEX uq_product_image_primary ON product_image (product_id) WHERE is_primary;
ALTER TABLE product_image ALTER COLUMN data SET STORAGE EXTERNAL;
```

- Deferred unique on `position` lets two images swap slots in one transaction.
- `STORAGE EXTERNAL` skips compressing already-compressed images.
- List queries never load `data` (SQLAlchemy `deferred()`).
- Migration runs after TV2's `product` migration.

## Validation

Runs before the transaction opens.

1. Over 5 MB → 413; empty → 422.
2. Type from magic bytes only (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WebP `RIFF`…`WEBP`); anything else → 415.
3. Optional Pillow `verify()`; corrupt → 422.
4. SHA-256 as lowercase hex.

## API

Base path `/api/products/{pid}/images`. Writes need a session, CSRF and `If-Match`; responses return the new `product.version`. Metadata never includes `data`.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/` | 200, list by `position` |
| POST | `/` (multipart `file`, `alt_text?`) | 201 |
| PUT | `/{iid}/file` | 200, same `id` |
| PATCH | `/{iid}` (`alt_text?`, `position?`, `is_primary?`) | 200; no-op keeps version |
| DELETE | `/{iid}` | 204 |
| GET | `/{iid}/content` | 200, bytes, `ETag: "<sha256>"` |

| Status | `code` |
| --- | --- |
| 401 / 403 | `unauthenticated` / `csrf_failed` |
| 404 | `not_found` (missing, deleted, or another vendor's) |
| 409 | `version_conflict` (+ `current_version`), `image_limit_reached`, `duplicate_image` |
| 413 / 415 / 422 | `file_too_large` / `unsupported_type` / `invalid_image` |
| 428 | `precondition_required` |

## Concurrency

One transaction per write; locking the product row makes writes to one product run in sequence, so the limit of 5 holds.

1. `SELECT … FROM product WHERE id = :pid FOR UPDATE`.
2. Check owner and status (404), version (409), and image count on upload (409).
3. Write the image change; fix positions and primary.
4. `UPDATE product SET version = version + 1`.
5. `COMMIT`; any error rolls back everything.

## Image Manager UI

A standalone component: input `productId` + `productVersion`, emits the new version after each write.

- Grid of up to 5 thumbnails with primary marked; upload disabled at 5.
- Upload with preview and client pre-check; replace, alt text, set primary, reorder, delete.
- On 409 `version_conflict`: reload and keep the chosen file for one-click retry.

## Tests

Test IDs F01–F16, T02–T04, S05 are not defined yet; map these once they are.

| Area | Cases |
| --- | --- |
| Validation | Each format accepted; fake extension → 415; empty; 5 MB vs 5 MB + 1 byte |
| API | Happy paths; other vendor → 404; missing/stale `If-Match` → 428/409; 6th image; duplicate |
| Rollback | Failure before version update → nothing saved; bad replace keeps original |
| Concurrency | 4 images + 6 parallel uploads → 1 succeeds; same-version writes → one 409 |
| Constraints | Raw SQL with bad type, size mismatch, second primary → rejected |

Concurrency tests use real Postgres, `threading.Barrier`, and repeat 20 times.
