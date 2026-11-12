# Situs lain di proxy ini

Proxy Caddy server ini juga melayani situs yang bukan Paradise Task Tracker,
misalnya `cipl-saipem.paradiseperkasa.com`. Satu situs, satu berkas
`<nama>.caddy` di folder ini. `apps/proxy/Caddyfile.ce` mengimpor semuanya
lewat `import /etc/caddy/sites/*.caddy`.

Isi berkasnya blok situs Caddy biasa. Tidak perlu baris `tls`: opsi global
proxy sudah memakai `acme_dns` untuk semua situs, jadi situs baru cukup punya
CNAME `_acme-challenge.<nama>` ke akun acme-dns yang sama
(`HTTPS & Sertifikat` di vault).

## Memasang atau mengubah situs

```bash
cp cipl-saipem.caddy ~/paradise-app/paradise/sites/
docker exec proxy caddy reload --config /etc/caddy/Caddyfile
```

`caddy reload` memeriksa seluruh konfigurasi dulu. Kalau isinya salah, reload
ditolak dan proxy tetap memakai yang lama. Tidak ada container yang dibuat ulang
dan tidak ada sambungan yang putus.

## Yang tidak boleh

Jangan menempelkan baris `import` atau blok situs ke `/etc/caddy/Caddyfile` di
container yang sedang berjalan. `paradise/bin/deploy.sh` membandingkan isi berkas
itu dengan yang ada di image; kalau berbeda, deploy berikutnya membuat ulang
SEMUA service dan tempelan itu hilang.

Berkas `*.caddy` di sini diabaikan git (`.gitignore`), jadi `git pull` dan
`deploy.sh` tidak menyentuhnya. Folder lain bisa dipakai dengan
`PROXY_SITES_DIR` di `.env`.
