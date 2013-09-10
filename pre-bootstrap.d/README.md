# pre-bootstrap.d

Executable files within this directory will be run via run-parts(8) before the
`knife bootstrap` takes place.

Don't use an extension for files placed in these directories, otherwise they
will not be recognized by run-parts(8).
