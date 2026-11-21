# Other sites on this proxy

This server's Caddy proxy also serves sites that aren't Paradise Task Tracker,
for example `cipl-saipem.paradiseperkasa.com`. One site, one `<name>.caddy` file
in this folder. `apps/proxy/Caddyfile.ce` imports them all with
`import /etc/caddy/sites/*.caddy`.

A file holds an ordinary Caddy site block. No `tls` line is needed. The proxy's
global options already use `acme_dns` for every site, so a new site only needs a
`_acme-challenge.<name>` CNAME pointing to the same acme-dns account
(`HTTPS & Sertifikat` in the vault).

## Installing or changing a site

```bash
cp cipl-saipem.caddy ~/paradise-app/paradise/sites/
docker exec proxy caddy reload --config /etc/caddy/Caddyfile
```

`caddy reload` validates the whole configuration first. If the content is wrong,
the reload is rejected and the proxy keeps using the old one. No container is
recreated and no connection drops.

## What not to do

Don't paste an `import` line or a site block into `/etc/caddy/Caddyfile` in the
running container. `paradise/bin/deploy.sh` compares that file's content with the
one in the image. If they differ, the next deploy recreates ALL services and the
pasted lines are lost.

The `*.caddy` files here are ignored by git (`.gitignore`), so `git pull` and
`deploy.sh` don't touch them. Another folder can be used with `PROXY_SITES_DIR`
in `.env`.
