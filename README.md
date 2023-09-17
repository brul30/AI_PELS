# Hotel Reservation Flask

Welcome to the **AI PELS (name subjet to change)** project! Follow these steps to set up your Python development environment and run the project locally.

## Prerequisites

- [Python](https://www.python.org/downloads/) installed on your system.
  
## Getting Started

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/brul30/AI_PELS.git
    cd AI_PELS
    ```

To install packages and run various command shortcuts, we use [rav](https://github.com/jmitchel3/rav). Open `rav.yaml` to see the various commands available if you prefer to not use `rav`.

_macOS/Linux Users_
```bash
python3 -m venv venv
source venv/bin/activate
venv/bin/python -m pip install pip pip-tools rav --upgrade
venv/bin/rav run installs
rav run freeze
```


_Windows Users_
```powershell
c:\Python310\python.exe -m venv venv
.\venv\Scripts\activate
python -m pip install pip pip-tools rav --upgrade
rav run win_installs
rav run win_freeze
```

With all the configuration done, here are the main commands you'll run:

```
rav run server
```

- `rav run server` maps to `python manage.py runserver` in the `src` folder


## Deactivate the Virtual Environment

When you're done working on the project, deactivate the virtual environment:

```bash
deactivate
