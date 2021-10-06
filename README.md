# cf-ddns
CloudFlare-based dynamic DNS stuff

## Installing
```shell
git clone https://github.com/EEKIM10/cf-ddns
cd cf-ddns
python3 -m pip install -U --user requests python-dotenv pip
```
Once you've done that, you can either
### Run interactively
```shell
python3 ddns.py
# Prompts will follow here, make sure you've got a keyboard handy
```
or
### Run headless
This is ideal for systems like crontabs

So, lets say, we own domain `example.com` - this is our **zone** (name)

Furthermore, in the DNS section on dash.cloudflare.com for example.com, there's a row: `foo`. `foo` has the record type `A` and points to `1.2.3.4`.
The **record name** here would be `foo.example.com`, and the **content** would be `1.2.3.4`.
If the record is proxied through cloudflare (the orange cloud), then `proxied` would be `true`
Otherwise, it's `false`.

Lets compile this into a command-line that creates/updates a record in our zone:

```shell
python3 iso-ddns.py --zone example.com --record-name foo.example.com
```

This will:
* If the record `foo` does not exist, it will create it, with the value of our current IP. It will be proxied if `--create-is-proxied` is passed.
* If the record `foo` does exist, it will update the `content` with out current IP. The proxy status _will not change_.

#### Top Tip:
If you are running `iso-ddns.py` in a crontab, for example, it is recommended to set `--exit-mode`.
`--exit-mode` has two values:
* `soft`
* `hard`

If exit mode is `soft`, the program will exclusively exit with exit code `1` if a crash happens.

However, if exit mode is `hard`, the error will not be captured and will be up to your shell to deal with it.

**Exit code 0 is always returned when the script successfully runs.**

## Environment variables
The following values can be configured in a `.env` file, or however you configure your environment variables.

* `DEBUG_LEVEL` - 0, 1 or 2. `0` is OFF, `1` simply logs whe there's a request made, and `2` logs the result of aforementioned request.
* `CF_TOKEN` - string, the token that allows you to access the cloudflare API ([Make sure you select `API Tokens`, not `API Keys`!](https://dash.cloudflare.com/profile/api-tokens))
