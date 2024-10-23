## Overview

Scans a mailbox in mbox format looking for certain terms in the subject, to, from and email body. It will output the raw emails in `.output\config-filename\raw` as well as text dumps in `.output\config-filename\text`. The text dumps will pretty print html emails as text where possible. Any word or PDF attachments will also be outputted to the `text` directory.

## Requirements

- Python 3

## Setup

- On linux / osx run `setup_env.sh`
- On windows run `setup_env.bat`

## Usage

You can run `python scan.py -h` to see all the command line arguments. The only required options is the config file which specifies the search terms to use.

```
python scan.py options.json
```

Currently you need to name the mailbox to be searched as `mailbox.mbox`.

## Example options file

```json
{
  "generalSearchTerms": ["slater", "martin", "ms"],

  "subjectSearchTerms": ["slater", "martin", "ms"],

  "fromSearchTerms": ["mslater"],

  "toSearchTerms": ["mslater"]
}
```
