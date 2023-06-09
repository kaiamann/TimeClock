# TimeClock

![Ubuntu Build](https://github.com/kaiamann/TimeClock/actions/workflows/python-app.yml/badge.svg)

A minimal CLI that allows keeping track of working hours. Also provides users with summary functionality.

## Installation

1. Make sure you have a working [Python](https://www.python.org/) installation. 
In case you do not have Python installed, you can install it via [Anaconda](https://www.anaconda.com/download). Simply follow the [installation instructions](https://docs.anaconda.com/free/anaconda/install/index.html).
2. In case you want to install the module into a new `venv`, make sure that it comes with `pip`:
    ```
    python -m pip --version
    ```
    For conda managed `venvs` install `pip` with:
    ```
    conda install pip
    ```

2. Clone this repo via `HTTP`:
    ```
    git clone https://github.com/kaiamann/TimeClock.git
    ```
    Or via `SSH`:
    ```
    git clone git@github.com/kaiamann/TimeClock.git
    ```

3. Navigate to the repo.
    ```
    cd TimeClock
    ```
4. Install via `pip`:
    ```
    pip install .
    ```

5. To initilaize run:
    ```
    timeclock
    ```
    This will take you though the configuration process.
    The configuration file will be saved in `~/.timeclock.yml`.
    You can directly edit it with an editor of your chioce, or just run
    ```
    timeclock config
    ```
    to go through the configuration again.


## Time tracking:
The primary feature of this CLI is time tracking, which can be started and stopped with:
```
timeClock
```
Upon ending the session, you will be asked to enter some keywords about what you did.
In case the devil possesses you and you start working on a weekend or a holiday, the session will automatically be moved to the next working day.


## Summaries:
Using the `summary` subcommand you can get a summary about yur working hours:
```
timeclock summary
```
Per default this will display how much you worked today and how much you still have to do.

### Timeframes
You can widen the timeframe by providing `summary` with some flags:
- `-w`, `--week`: Gives a summary over the whole week.
- `-m`, `--month`: Gives a summary over the whole month.

### Go Back in time:
You can also specify a particular day with the `-d`, `--date` flag followed by a date. It also works with the `-w` and `-m` flags. E.g.:
```
$ timeclock summary -w -d "20 April 2023"
Summary for 01 April 2023 - 30 April 2023:
2 holiday/s in this period:
Fri: 07 April 2023 - Good Friday
Mon: 10 April 2023 - Easter Monday
Worked for: 107 Hours 11 Minutes
To be done: 0 Hours 49 Minutes
```
will give the summary for thar particular period.
It will also display any holidays in this timeframe.

### Filtering
Remember the keywords you enterd when finishing your work session?
You can use them to keep track of how much time you spent on a particular project using the `-k`, `--keywords` flag:
```
timeclock summary -k "SomeKeyword"
```
This will only count sessions where these particular keywords occurs in the description.

## Version Control
Coming soon:tm:

## Fancy stuff
If you want to enable tab completion for the timeclock, add this line to your `.bashrc`:
```
eval "$(register-python-argcomplete timeclock)"
```
Currently this only supports the subparsers and their flag options.
