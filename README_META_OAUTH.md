# Facebook Page connection

The account manager now supports connecting Facebook Pages directly from the local UI. The user does not manually enter a Page access token.

## Meta App setup

Create a Meta app with Facebook Login configured for web and add the callback URL exactly as:

```text
http://localhost:8000/api/oauth/facebook/callback
```

Configure these server environment variables:

```text
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_GRAPH_API_VERSION=v26.0
META_OAUTH_REDIRECT_URI=http://localhost:8000/api/oauth/facebook/callback
```

`v26.0` is the current Graph API release as of July 29, 2026. The Graph API is versioned, so keep the version in configuration instead of hard-coding it throughout the application.

For Page listing and publishing, the connection requests:

- `public_profile`
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

Meta's permissions reference documents `pages_manage_posts` as the permission used to create, edit and delete Page posts, including video posts, with `pages_read_engagement` and `pages_show_list` listed as dependencies.

## UI flow

1. Open **Upload Old Video**.
2. Under **Connected Upload Accounts**, choose **Facebook Page**.
3. Click **Connect Facebook & Select Pages**.
4. Complete Meta login/authorization in the popup.
5. The app discovers Pages through `/me/accounts` on the server.
6. Select one or more Pages in the UI.
7. The server stores the Page access token in `tokens/meta_<page>.json` with a restrictive file mode where supported.
8. The account registry stores only the account ID, Page ID and credential reference; credential reference and token are not returned by the public account list endpoint.

## Important

The Meta App still needs the appropriate product configuration and permission access for the use case. Meta can require App Review / screencast requirements for permissions such as `pages_manage_posts`. The local UI cannot bypass those Meta requirements.

The current change implements the secure connection/account-discovery layer. The existing Facebook uploader remains a separate adapter and can be enabled independently once its publishing implementation is completed and tested against a real Page.

## Runtime setup

Set the four `META_*` environment variables before starting the local server; no Meta secret is stored in the repository.
