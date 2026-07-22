# Synkron Google Merchant feed

This public repository is the publication target for Synkron Shop's Google
Merchant Center product feed. A scheduled Zoho Flow reads active products from
Zoho Commerce, generates RSS 2.0 XML, and updates
[`synkron-google-products.xml`](synkron-google-products.xml) through GitHub's
Contents API.

```text
Zoho Flow schedule
  -> Deluge custom function
  -> Zoho Commerce Products API
  -> Google Merchant RSS XML
  -> GitHub Contents API
  -> raw.githubusercontent.com
  -> Google Merchant Center
```

The repository side of the integration is ready. The account-specific steps in
Zoho Flow and Google Merchant Center still need to be completed by an account
administrator.

## Repository contents

- `synkron-google-products.xml` is the initial, well-formed public feed. The
  first successful Flow run replaces it with product items.
- `deluge/generate_synkron_google_feed.dg` is the custom function to paste into
  Zoho Flow.
- `scripts/validate_feed.py` validates the generated file without third-party
  packages.
- `.github/workflows/validate-feed.yml` validates every feed update.

## 1. Create the two Zoho Flow connections

### Zoho Commerce

In **Zoho Flow -> Settings -> Connections**, create and authorize a Zoho
Commerce connection using the account that owns the Synkron Shop organization.
Record its **connection link name** from **View Details**.

### GitHub

1. Create a fine-grained GitHub personal access token for only
   `muchelle-alvin/synkron-google-merchant-feed`.
2. Grant the token **Repository permissions -> Contents: Read and write** and no
   unrelated permissions.
3. In **Zoho Flow -> Settings -> Auth Profiles**, create an API-key profile:

   | Setting | Value |
   | --- | --- |
   | Parameter name | `Authorization` |
   | Placement | Header |
   | Field type | Password/secret |
   | Test method | `GET` |
   | Test URL | `https://api.github.com/user` |

4. Create a connection from this profile. Enter the value as `Bearer ` followed
   by one space and the token. Record the connection's **link name**.

Never commit the token or an organization credential to this repository.

## 2. Install the custom function

In `deluge/generate_synkron_google_feed.dg`, replace these two quoted values with
the connection link names from Zoho Flow:

```text
REPLACE_WITH_ZOHO_COMMERCE_CONNECTION_LINK_NAME
REPLACE_WITH_GITHUB_CONNECTION_LINK_NAME
```

In the Flow builder, create a custom function named
`generate_synkron_google_feed` with return type **Map** and these inputs:

| Parameter | Type | Value |
| --- | --- | --- |
| `commerce_api_base` | String | `https://commerce.zoho.com` |
| `organization_id` | String | Synkron Commerce organization ID |
| `storefront_domain` | String | Published shop hostname, without `https://` or a trailing slash |
| `currency_code` | String | `KES` |
| `github_owner` | String | `muchelle-alvin` |
| `github_repo` | String | `synkron-google-merchant-feed` |
| `github_branch` | String | `main` |
| `github_path` | String | `synkron-google-products.xml` |

Paste the complete Deluge source into the function editor and save it. The
Commerce connection needs the `ZohoCommerce.items.READ` scope.

The Commerce organization ID can be read in the logged-in Commerce browser
console with:

```javascript
app.data.books_org_id
```

## 3. Schedule and test the Flow

1. Add a daily schedule trigger for **11:00 PM** in the organization timezone.
2. Confirm the organization timezone is **Africa/Nairobi (GMT+03:00)**.
3. Add the custom function after the schedule and supply the values above.
4. Run **Test & Debug**.

A successful first run returns `status: "success"`. A later run with identical
catalog data returns `status: "unchanged"`; both are healthy outcomes. The
function deliberately refuses to overwrite a working feed when it generates
zero items.

Then confirm that the raw URL opens without authentication and contains product
`<item>` elements:

```text
https://raw.githubusercontent.com/muchelle-alvin/synkron-google-merchant-feed/main/synkron-google-products.xml
```

## 4. Add the source to Google Merchant Center

Choose **Add products from a file -> Enter a link to your file** and use the raw
URL above. Configure the fetch for daily at **12:00 AM GMT+03:00**, after the
Flow has run.

Start with:

| Setting | Value |
| --- | --- |
| Country | Kenya |
| Language | English |
| Feed label | `SYNKRON_KE` |
| Marketing methods | All applicable methods |

Add countries only after shipping, currency, tax, checkout, and delivery are
configured for them. Review product diagnostics under **Products -> Needs
attention** after Google's first fetch.

## Local validation

The checked-in seed feed intentionally has no items. Validate it with:

```bash
python3 scripts/validate_feed.py --allow-empty synkron-google-products.xml
python3 -m unittest discover -s tests -v
```

To validate a generated production feed and require at least one product, omit
`--allow-empty`.

## Operational limits

The function fetches at most 10 pages of 200 products. Zoho Flow also imposes
Deluge statement and execution limits, so catalogs with many products or
variants may need batching or a move to Zoho Catalyst. The function reports the
number of written and skipped variants to make that behavior visible.

## Reference documentation

- [Zoho Commerce: List All Products](https://www.zoho.com/commerce/api/list-all-products.html)
- [Zoho Deluge: `invokeURL`](https://www.zoho.com/deluge/help/webhook/invokeurl-api-task.html)
- [GitHub: Create or update file contents](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents)
- [Google Merchant Center: RSS 2.0 specification](https://support.google.com/merchants/answer/14987622?hl=en)
- [Google Merchant Center: Product data specification](https://support.google.com/merchants/answer/7052112?hl=en)
