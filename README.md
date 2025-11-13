# namecheck

<p align="left" width="250">
    <a href="https://github.com/pixelprotest/namecheck/actions">
        <img src="https://github.com/pixelprotest/namecheck/actions/workflows/tests.yml/badge.svg" alt="Tests Status">
    </a>
    <a href="">
        <img src="https://img.shields.io/github/v/release/pixelprotest/namecheck">
    </a>
    <a href="">
        <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue">
    </a>
    <a href="https://github.com/pixelprotest/namecheck/blob/main/LICENSE">
        <img src="https://img.shields.io/badge/license-MIT-blue?style=flat">
    </a>
</p>

CLI utility to check the availability of project names on PyPi and TestPyPi

<img alt="Demo" width="100%" style="border-radius:20px;" src="https://raw.githubusercontent.com/pixelprotest/namecheck/main/.github/demo.gif">

## 📦 Installation
Simple pip install
```
pip install namecheck
```

_* Note since TestPyPi blocks non-javascript requests, some of the direct project lookups are done using [playwright-python](https://github.com/microsoft/playwright-python). After installing `namecheck`, it will ask you to install playwright on your system._

## 🚀 Usage
To launch just run

```bash
namecheck
```

To speed up launch times, the app stores the package names from PyPi and TestPyPi into a cache. If you pass in the `--refresh` flag, it will clear this cache and do a fresh lookup.

```bash
namecheck --refresh
```

## License

MIT License. This project is for personal use.