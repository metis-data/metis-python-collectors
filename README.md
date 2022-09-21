# Metis Flask SQLAlchemy instrumentation

## How to instrument



## To build the package

```shell
# in the root of the project run the following command
python3 setup.py sdist

# to install the package from local folder
python3 -m pip install ~/<path-to-root-folder>/dist/sqlalchemycollector-0.0.1.tar.gz
```


## To run the demo app
```shell
cd ./demo-app
python3 -m venv venv
pip install -r requirements.txt
python bookmanager.py
```

## Verbose logging
* By default the verbose logging is disabled
* In order to enable it, one needs to set the environment variable METIS_LOGGER_ULTRA_VERBOSE. E.g.:
    ```commandline
    export METIS_LOGGER_ULTRA_VERBOSE=            # The "=" is important
    ```
* Once enabled, the verbose logging is working in its maximal verbosity mode.
* By default, it logs everything to stdout. In order to log into a file instead, set the METIS_LOGGER_FILENAME environment variable. E.g.:
    ```commandline
    export METIS_LOGGER_FILENAME=/tmp/my_app.log
    ```
* The following variables can be used in order to shorten the amount of logging:
  * METIS_LOGGER_SKIP_PARAMS - used to disable method parameters printing. E.g.:
    ```commandline
    export METIS_LOGGER_SKIP_PARAMS=
    ```
  * METIS_LOGGER_SKIP_RETURN_VALUE - used to disable method return values. E.g.:
    ```commandline
    export METIS_LOGGER_SKIP_RETURN_VALUE=
    ```
  * METIS_LOGGER_MAX_LOGGING_SIZE
    * once verbose logging exceeds METIS_LOGGER_MAX_LOGGING_SIZE characters, stop logging. E.g.:
      ```commandline
      export METIS_LOGGER_MAX_LOGGING_SIZE=1000000   # Stop writing the verbose logging after 1M characters
      ```
  * METIS_LOGGER_MAX_CALLS - limit the maximal logs per Python method. The format is ```method1=limit1,method2=limit2,...``` E.g.:
    ```commandline
    export METIS_LOGGER_MAX_CALLS=sqlalchemycollector.alchemy_instrumentation.fix_sql_query=10000,sqlalchemycollector.alchemy_instrumentation.before_query_hook=10000,sqlalchemycollector.exporters.file_exporter.export_to_file=5000
    ```
    Note that the method's **full name** should be specified. I.e., the module full name concatenated with the method name.
    * The limit value is per process and is defined the same for all processes.
  * METIS_LOGGER_LEVEL - is used to set the minimal logging level. The default is "debug". Its possible values are python's "logging" logging level names. I.e., "debug", "info", "warning", "error", "critical". E.g.:
    ```commandline
    export METIS_LOGGER_LEVEL=info
    ```
* In order to include a method to the verbose logging printing and stats, one need to add a @log decorator to the method. E.g.:
  ```python
  @log
  def my_great_method(self):
    pass
  ```
* The later log orchestration excepts all exceptions. If the user likes to disable this behaviour, she should use the ```True``` parameter of @log:
  ```python
  @log(True)
  def my_great_method(self):
    pass
  ```
* At the end of the program, the verbose logging prints stats tables. E.g., in the case the program runs using two processes:
  ```commandline
     # Calls   | # Exceptions | # Total Time | Method (pid=149933)
  -------------+--------------+--------------+-------------------------------------------------------------------------------
       1       |      1       |   0.931ms    | sqlalchemycollector.instruments.__init__
      34       |      0       | 2483.717ms   | sqlalchemycollector.alchemy_instrumentation.before_query_hook
       5       |      0       |  14.996ms    | sqlalchemycollector.exporters.file_exporter.export
       1       |      0       |  12.614ms    | sqlalchemycollector.instruments.instrument_app
       1       |      0       |   9.532ms    | sqlalchemycollector.alchemy_instrumentation._instrument
      11       |      0       |   9.154ms    | sqlalchemycollector.exporters.file_exporter.export_to_file
      17       |      0       |   6.615ms    | sqlalchemycollector.alchemy_instrumentation.fix_sql_query
       1       |      0       |   1.563ms    | sqlalchemycollector.instruments.setup
       1       |      0       |   0.416ms    | sqlalchemycollector.instruments.set_exporters
      14       |      0       |   0.382ms    | sqlalchemycollector.alchemy_instrumentation.add_quote_to_value_of_type_string
       1       |      0       |   0.339ms    | sqlalchemycollector.instruments._set_exporters
       1       |      0       |   0.272ms    | sqlalchemycollector.instruments._build_resource
       1       |      0       |   0.01ms     | sqlalchemycollector.instruments._convert_items_to_metis_tags
       1       |      0       |   0.007ms    | sqlalchemycollector.alchemy_instrumentation.__init__
       1       |      0       |   0.006ms    | sqlalchemycollector.instruments._add_processor
       1       |      0       |   0.004ms    | sqlalchemycollector.exporters.file_exporter.__init__


     # Calls   | # Exceptions | # Total Time | Method (pid=149931)
  -------------+--------------+--------------+--------------------------------------------------------------
       1       |      1       |   0.891ms    | sqlalchemycollector.instruments.__init__
       1       |      0       |  15.219ms    | sqlalchemycollector.instruments.instrument_app
       1       |      0       |  10.489ms    | sqlalchemycollector.alchemy_instrumentation._instrument
       1       |      0       |   1.507ms    | sqlalchemycollector.instruments.setup
       1       |      0       |   0.446ms    | sqlalchemycollector.instruments.set_exporters
       1       |      0       |   0.384ms    | sqlalchemycollector.instruments._set_exporters
       1       |      0       |   0.211ms    | sqlalchemycollector.instruments._build_resource
       1       |      0       |   0.007ms    | sqlalchemycollector.instruments._convert_items_to_metis_tags
       1       |      0       |   0.007ms    | sqlalchemycollector.alchemy_instrumentation.__init__
       1       |      0       |   0.005ms    | sqlalchemycollector.instruments._add_processor
       1       |      0       |   0.004ms    | sqlalchemycollector.exporters.file_exporter.__init__
  ```
  The methods that had exceptions are noted first. The next lines are each one of the methods ordered by the total time spend running the method.