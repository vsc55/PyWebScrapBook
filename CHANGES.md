## General notes
* This project generally follows [semantic versioning](https://semver.org/). For a version `x.y.z`, `x` means a major (backward incompatible) change, `y` means a minor (backward compatible) change, and `z` means a patch (bug fix). Few versions may not strictly follow this rule due to historical reasons, though.
* Versions before 1.0 are in initial development. APIs are not stable for these versions, even a `y` version can involve a breaking change, and only partial significant changes are summarized in this document. See full commit history in the source repository for details.
* Client requirement in this document refers to the version of [`WebScrapBook`](https://github.com/danny0838/webscrapbook) browser extension.

## Version 0.23.0
* Bumped client requirement to >= 0.79.
* Adjusted locking mechanism:
  * A lock is now created under `.wsb/locks` instead of `.wsb/server/locks`.
  * A lock is now created as a file instead of a folder.
  * A lock is now created with an ID, and can be extended using the same ID. Releasing a lock now requires its ID.
  * The server now responses 503 rather than 500 for a timeout of `lock` server action.
* Added cache, check, and convert commands.

## Version 0.22.0
* Removed shebang for script files.

## Version 0.21.0
* A lock is now created using a hashed filename instead of a plain filename.

## Version 0.20.0
* Added content security policy restriction for served web pages. They can no longer send AJAX requests and form actions to prevent a potential attack. A config `app.content_security_policy` is added to change the behavior.

## Version 0.18.1
* Installation requirement is now declared as Python >= 3.6. Note that version compatibility is not thoroughly checked for prior versions, and some functionalities are known to break in Python < 3.7 for some versions despite marked as installable.
* Response of a server`config` action now exposes a new `WSB_EXTENSION_MIN_VERSION` value, which informs the client to apply self version checking.

## Version 0.17.0
* Bumped client requirement to >= 0.75.6.
* Bumped requirement of `werkzeug` to >= 1.0.0.
* Removed `cryptography` from installation requirement. It is now an optional requirement (for ad hoc SSL key generating).
* Fixed a bug for zip editing through server actions in Python < 3.7.
* Response 404 rather than 400 for `list` server action when the directory is not found.
* Added unit tests.

## Version 0.15.0
* Tokens are now created under `.wsb/server/tokens` instead of `.wsb/server/token`.

## Version 0.14.0
* Switched backend server framework to `Flask` from `Bottle`.
* Added support for `app.allow_x_*` configs to prevent issues when serving behind a reverse proxy.
* Dropped support for `server.ssl_pw` config.

## Version 0.11.0
* Added support of zip editing through server actions.

## Version 0.8.0
* Added support for `book.*.no_tree` config.
