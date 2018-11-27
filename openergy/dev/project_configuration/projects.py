import pandas as pd

from openergy import get_client, get_odata_url, get_full_list

from . import Organization


class Project:

    def __init__(self, info):
        '''

        Parameters
        ----------
        info: dictionary
            A dictionary that contains at least id and name keys
        '''

        if ("id" in info.keys()) and ("name" in info.keys()):
            self._info = info
            self.__dict__.update(info)
        else:
            raise ValueError("The info must contain at least 'id' and 'name' field")

    @classmethod
    def retrieve(cls, organization_name=None, name=None, id=None, odata=None):
        '''
        Retrieve project detailed info and create a Project instance.
        You need to give either the organization's name and the project's name or the project id or the project odata id

        Parameters
        ----------
        organization_name: string

        name: string

        id: uuid-string

        odata: uuid-string

        Returns
        -------

        The Project instance.

        '''
        client = get_client()
        if id is None:
            if odata is None:
                if (organization_name is None) or (name is None):
                    raise ValueError("Please indicate at least an id or an organization name and a project name "
                                     "so that the project can be retrieved")
                else:

                    r = client.list(
                        "/oteams/projects/",
                        params={
                            "name": name,
                            "organization": Organization.retrieve(organization_name).id
                        }
                    )["data"]

                    if len(r) == 0:
                        return
                    elif len(r) == 1:
                        id = r[0]["id"]
            else:
                r = client.retrieve(
                    "/odata/projects/",
                    odata
                )
                id = r["base"]

        info = client.retrieve(
            "oteams/projects",
            id
        )

        return cls(info)

    def get_detailed_info(self):
        """

        Returns
        -------

        A dictionary that contains all info about the Project

        """

        client = get_client()

        info = client.retrieve(
            "oteams/projects",
            self.id
        )

        self._info = info
        self.__dict__.update(info)

        return self._info

    def get_organization(self):
        return Organization.retrieve(self.organization["id"])

    def update(
        self,
        name=None,
        comment=None,
        display_buildings=None,
    ):

        args = ["name", "comment", "display_buildings"]
        params = {}
        for arg in args:
            if locals()[arg] is not None:
                params[arg] = locals()[arg]

        if len(params.keys()) > 0:
            client = get_client()
            client.partial_update(
                "oteams/projects",
                self.id,
                data=params
            )

        self.get_detailed_info()

    def delete(self):

        client = get_client()

        name = self.name

        client.destroy(
            "oteams/projects",
            self.id
        )

        for k in self._info.keys():
            setattr(self, k, None)

        self._info = None

        print(f"The project {name} has been successfully deleted")

    def _get_resource_classes(self):

        # Touchy imports
        from . import Gate, Importer, Cleaner, Analysis

        return {
            "gate": Gate,
            "importer": Importer,
            "cleaner": Cleaner,
            "analysis": Analysis
        }

    def get_all_resources(self, models=["gate", "importer", "cleaner", "analysis"]):

        """
        Retrieve several resources of the project

        Parameters
        ----------
        models: array default ["gate", "importer", "cleaner", "analysis"] (All)
            The models you want to retrieve.

        Returns
        -------
        A dictionary with asked models as keys and the list of Resource Instances as values.

        """

        classes = self._get_resource_classes()
        resources = {}

        for model in models:
            r = get_full_list(
                get_odata_url(model),
                params={
                    "project": self.odata
                }
            )

            resources[model] = [classes[model](info) for info in r]

        return resources

    def get_resource(self, model, name):
        """
        Retrieve a single resource of the project

        Parameters
        ----------
        model: string
            choices are "gate", "importer", "cleaner", "analysis"
        name: string
            The name of the resource

        Returns
        -------

        A Resource Instance.

        """

        r = get_full_list(
            get_odata_url(model),
            params={
                "name": name,
                "project": self.odata
            }
        )

        if len(r) == 0:
            print(f"No {model} named {name} found in project {self.name}")
            return None
        else:
            return self._get_resource_classes()[model](r[0])

    def get_gate(self, name):
        """

        Parameters
        ----------
        name: gate name

        Returns
        -------
        A Gate Instance.

        """
        return self.get_resource("gate", name)

    def get_importer(self, name):
        """

        Parameters
        ----------
        name: importer name

        Returns
        -------
        An Importer Instance.

        """
        return self.get_resource("importer", name)

    def get_cleaner(self, name):
        """

        Parameters
        ----------
        name: cleaner name

        Returns
        -------
        A Cleaner Instance.

        """
        return self.get_resource("cleaner", name)

    def get_analysis(self, name):
        """

        Parameters
        ----------
        name: analysis name

        Returns
        -------
        An Analysis Instance.

        """
        return self.get_resource("analysis", name)

    def data_scan(self):
        """


        Returns
        -------
        A dataframe containing

        """
        resources = self.get_all_resources(["importer", "cleaner", "analysis"])
        df_project = pd.DataFrame()
        for resource_model, resources_list in resources.items():
            for res in resources_list:
                df_res = res.data_scan()
                df_project = pd.concat([df_project, df_res], ignore_index=True)
        return df_project

    def check_last_files(self,paths_dict=None, all_gates=True, default_limit=10):
        """
        Parameters
        ----------

        paths_dict: dictionary, default None
            Keys: gates names
            Values: List of path and files limit

            Example: {
                "gate1": [
                    {
                        "path": "path1_1",
                        "limit": limit1_1
                    },
                    {
                        "path": "path1_2",
                        "limit": limit1_2
                    }
                ],
                "gate2": [
                    {
                        "path": "path2_1",
                        "limit": limit2_1
                    }
                ]
            }

        all_gates: boolean, default True
            Display the last files of project's gates (at root) even if not in the paths_dict

        default_limit: integer, default 10
            The number of displayed last files when not precised

        Returns
        -------

        The last files of each gate of the project as a dictionary
        """

        if paths_dict is None:
            paths_dict = {}

        gates_list = self.get_all_resources(models=["gate"])["gate"]
        last_files = {}
        for g in gates_list:
            if g.name in paths_dict.keys():
                for path_and_limit in paths_dict[g.name]:
                    path =  path_and_limit.get("path", "/")
                    limit = path_and_limit.get("limit", default_limit)
                    last_files[f"{g.name}@{path}"] = g.check_last_files(path, limit)
            else:
                if all_gates:
                    last_files[f"{g.name}@/"] = g.check_last_files("/", default_limit)

        return last_files

    def create_internal_gate(
        self,
        name,
        crontab,
        script,
        comment="",
        timezone="Europe/Paris",
        replace=False,
        activate=True,
        waiting_for_a_file=False,
        sleep_loop_time=15,
        abort_time=180,
        passive=False
    ):
        """

        You must have creation rights within the project

        Parameters
        ----------
        name: string

        crontab: string
            6 characters to set the execution frequency of the importer
            (see https://platform.openergy.fr/docs/glossaire.html?highlight=crontab#crontab)

        script: string
            The feeding script

        comment: string
            An optional comment

        timezone: srting default "Europe/Paris"

        replace: bool default False
            replace if a gate with the same name already exists

        activate: bool default True
            activate the gate directly after creation

        passive: bool default False
            create a passive gate

        Returns
        -------

        A Gate Instance

        """

        # Touchy import
        from . import Gate

        client = get_client()

        #verify if it exists already
        g = self.get_resource("gate", name)
        if g is not None:
            print(f"Gate {name} already existed")
            if not replace:
                return
            else:
                print(f"Deleting current gate {name}")
                g.delete()

        print(f"Creation of new gate {name}")
        gate_info = client.create(
            get_odata_url("gate"),
            data={
                "project": self.odata,
                "name": name,
                "comment": comment
            }
        )
        print(f"The gate {name} has been successfully created")
        gate = Gate(gate_info)
        gate.create_oftp_account()

        if not passive:
            base_feeder = gate.create_base_feeder(timezone, crontab)
            base_feeder.create_generic_basic_feeder(script)
            if activate:
                gate.activate()
                print(f"The gate {name} has been successfully activated")

                if waiting_for_a_file:
                        gate.wait_for_a_file(sleep_loop_time, abort_time)



        return gate

    def create_external_gate(
            self,
            name,
            custom_host,
            custom_port,
            custom_protocol,
            custom_login,
            password,
            comment="",
            replace=False
    ):
        """

        You must have creation rights within the project

        Parameters
        ----------
        name: string

        host: string
            The ftp host name

        port: integer
            The port number

        protocol: string
            "ftp", "sftp" or "ftps"

        login: string
            The login of your ftp credetials

        password: string
            The password of your ftp credentials

        comment: string
            An optional comment

        replace: bool default False
            replace a Gate with the same name already exists

        Returns
        -------

        A Gate instance

        """

        from . import Gate

        client = get_client()

        # verify if it exists already
        g = self.get_resource("gate", name)
        if g is not None:
            print(f"Gate {name} already existed")
            if not replace:
                return
            else:
                print(f"Deleting current gate {name}")
                g.delete()

        print(f"Creation of new gate {name}")

        gate_info = client.create(
            get_odata_url("gate"),
            data={
                "project": self.odata,
                "name": name,
                "comment": comment
            }
        )

        print(f"The gate {name} has been successfully created")

        gate = Gate(gate_info)

        gate.update_external(
            custom_host=custom_host,
            custom_port=custom_port,
            custom_protocol=custom_protocol,
            custom_login=custom_login,
            password=password,
        )

        return gate

    def create_importer(
            self,
            name,
            gate_name,
            parse_script,
            root_dir_path="/",
            crontab="",
            re_run_last_file=False,
            comment="",
            activate=True,
            replace=False,
            waiting_for_outputs=False,
            outputs_length=0,
            sleep_loop_time=15,
            abort_time=180,
            waiting_for_cleaner_inputs=False
    ):
        """

        You must have creation rights within the project

        Parameters
        ----------

        importer_name: string
            The name of the importer

        gate_name: string
            The name of the gate to read files in

        parse_script: string
            The full python script to parse the files

        root_dir_path: string
            The path the importer starts to read files

        crontab: string
            6 characters to set the execution frequency of the importer
            (see https://platform.openergy.fr/docs/glossaire.html?highlight=crontab#crontab)

        re_run_last_file: boolean, default False
            Decides if the last file should be re-read by the importer at the beginning of each execution

        importer_comment: string, defaut ""
            An optional comment for the importer

        activate: boolean, default True
            True -> The importer get activated after creation

        replace: boolean, default False
            True -> If an importer with the same name already exists, it gets deleted and a new one get created
            False ->  If an importer with the same name already exists, a message informs you and nothing get created

        waiting_for_outputs: boolean, default False
            True -> Wait for the outputs to be created. (With activate=True only)

        outputs_length: int
            The number of expected outputs.

        waiting_for_cleaner_inputs: boolean, default False
            Wait for cleaner inputs to be ready

        Returns
        -------

        An Importer instance
        """

        # Touchy import
        from . import Importer

        client = get_client()

        # verify if it exists already
        i = self.get_resource("importer", name)
        if i is not None:
            print(f"Importer {name} already existed")
            if not replace:
                return
            else:
                print(f"Deleting current importer {name}")
                i.delete()

        print(f"Creation of importer {name}")

        importer_info = client.create(
            "/odata/importers/",
            data={
                "project": self.odata,
                "name": name,
                "comment": comment
            }
        )

        print(f"The importer {name} has been successfully created")

        importer = Importer(importer_info)

        importer.update(
            gate_name=gate_name,
            root_dir_path=root_dir_path,
            crontab=crontab,
            parse_script=parse_script,
            re_run_last_file=re_run_last_file,
            activate=False
        )

        if activate:
            importer.activate()
            print(f"The importer {name} has been successfully activated")

            if waiting_for_outputs and outputs_length>0:
                importer.wait_for_outputs(outputs_length, sleep_loop_time, abort_time)

                if waiting_for_cleaner_inputs:
                     importer.wait_for_cleaner_inputs(outputs_length, sleep_loop_time, abort_time)


        return importer

    def create_analysis(
            self,
            name,
            inputs_list,
            inputs_config_fct,
            output_names_list,
            outputs_config_fct,
            input_freq,
            output_freq,
            clock,
            output_timezone,
            script,
            start_with_first=False,
            wait_for_last=False,
            before_offset_strict_mode=False,
            custom_before_offset=None,
            custom_after_offset=None,
            custom_delay=None,
            wait_offset='6H',
            comment="",
            activate=True,
            replace=False,
            waiting_for_outputs=False,
            outputs_length=0
    ):
        """

        You must have creation rights within the project

        Parameters
        ----------

        name: string
            The name of the analysis

        inputs_list: list of series resources
            The script loops through this list to create the analysis_inputs according to the following function

        inputs_config_fct: function
            This function takes a series resource as argument and returns the associated input config

        output_names_list: list
            The list of the output names. You can't retrieve it from a test for the moment.
            The script loops through this list to create the analysis_outputs according to the following function

        outputs_config_fct: function
            This function takes the name of the output as argument and returns the associated output config

        input_freq: string (pandas freq format)
            The freq of the input dataframe

        output_freq: string (pandas freq format)
            the freq of the output dataframe

        clock: ["gmt", "dst", "tzt"]
            the clock of the output dataframe

        output_timezone: string
            the timezone of the output dataframe

        script: string
            the full analysis script

        start_with_first: boolean
            start analysis with first data ignoring custom offsets

        wait_for_last: boolean
            wait for all series to have data to launch analysis

        before_offset_strict_mode: boolean
            don't start analysis until the custom_before_offset is reached

        custom_before_offset: string (pandas freq format)
            the quantity of data before time t to compute the value at time t

        custom_after_offset: string (pandas freq format)
            the quantity of data after time t to compute the value at time t

        custom_delay: string (pandas freq format)

        wait_offset: string (pandas freq format)

        comment: string, defaut ""
            An optional comment for the analysis

        activate: boolean, default True
            True -> The analysis get activated after creation

        replace: boolean, default False
            True -> If an analysis with the same name already exists, it gets deleted and a new one get created
            False ->  If an analysis with the same name already exists, a message informs you and nothing get created


        Returns
        -------

        An Analysis Instance
        """

        #Touchy import
        from . import Analysis

        client = get_client()

        # verify if it exists already
        a = self.get_resource("analysis", name)
        if a is not None:
            print(f"Analysis {name} already existed")
            if not replace:
                return
            else:
                print(f"Deleting current analysis {name}")
                a.delete()

        print(f"Creation of analysis {name}")

        analysis_info = client.create(
            "odata/analyses",
            data={
                "project": self.odata,
                "name": name,
                "comment": comment
            }
        )

        print(f"The analysis {name} has been successfully created")

        analysis = Analysis(analysis_info)

        # inputs
        for input_se in inputs_list:
            input_config = inputs_config_fct(input_se)
            input_config["analysis"] = analysis.id
            client.create(
                "odata/analysis_inputs",
                data=input_config
            )

        # config

        client.create(
            "odata/analysis_configs",
            data={
                "analysis": analysis.id,
                # Basic
                "script_method": 'array',
                "input_freq": input_freq,
                "output_freq": output_freq,
                "clock": clock,
                "output_timezone": output_timezone,
                "script": script,

                # Expert
                "start_with_first": start_with_first,
                "wait_for_last": wait_for_last,
                "before_offset_strict_mode": before_offset_strict_mode,
                "custom_before_offset": custom_before_offset,
                "custom_after_offset": custom_after_offset,

                # Outputs
                "custom_delay": custom_delay,
                "wait_offset": wait_offset
            }
        )

        # outputs
        for output_name in output_names_list:
            output_config = outputs_config_fct(output_name)
            output_config["analysis"] = analysis.id
            client.create(
                "odata/analysis_outputs",
                data=output_config
            )

        if activate:
            analysis.activate()
            print(f"The analysis {name} has been successfully activated")

            if waiting_for_outputs:
                analysis.wait_for_outputs(outputs_length)

        return analysis

    def deactivate(self):
        """
        Deactivate all resources of the project (gates, importers, cleaners, analyses)

        """
        resources = self.get_all_resources()
        for model, res_l in resources.items():
            if model == "analysis":
                models = "analysis"
            else:
                models = f"{model}s"
            print(f"Deactivating all {models}")
            for res in res_l:
                res.deactivate()

