from typing import Dict, List, Tuple
import darshan
import os
import argparse
import pandas as pd

#####################################################
# Classes                                           #
#####################################################

class DXT_POSIX_metadata :
    id: int
    rank: int
    hostname: str
    write_count: int
    read_count: int

    def __init__(self, i_id, i_rank, i_hostname, i_write, i_read) :
        self.id = i_id
        self.rank = i_rank
        self.hostname = i_hostname
        self.write_count = i_write
        self.read_count = i_read

    def to_filename(self) :
        return "_".join([str(self.id), str(self.rank), self.hostname])

class DXT_POSIX_coll :
    metadata: List[DXT_POSIX_metadata]
    read_segments: Dict[str, pd.DataFrame]
    write_segments: Dict[str, pd.DataFrame]

    def __init__(self, posix_records: List):
        self.metadata = []
        self.read_segments = {}
        self.write_segments = {}

        for record in posix_records :
            record_metadata = DXT_POSIX_metadata(record["id"], record["rank"], record["hostname"], 
                                    record["read_count"], record["write_count"])
            self.metadata.append(record_metadata)

            # for now working under the assumption that the `id` of an entry is unique.
            #   if this does not hold, combine hostname + rank + id into a key.
            if record_metadata.id in self.read_segments.keys() :
                raise ValueError("ASSUMPTION FALSE: record IDs are not unique!")

            self.read_segments[record_metadata.id] = record["read_segments"]
            self.write_segments[record_metadata.id] = record["write_segments"]

    def export_parquet(self, directory:str, prefix: str) :
        # this version just spits every entry to its own file
        # we might want to join these for less file nonsense
        file_prefix = "DXTPOSIX"
        file_suffix = ".parquet"

        for record in self.metadata :
            file_id_prefix = record.to_filename()
            read_filename = file_prefix + "_" + prefix + "_" + file_id_prefix + "_read_segments" + file_suffix
            self.read_segments[record.id].to_parquet(os.path.join(directory, read_filename))
            
            write_filename = file_prefix + "_" + prefix + "_" + file_id_prefix + "_write_segments" + file_suffix
            self.write_segments[record.id].to_parquet(os.path.join(directory, write_filename))

##############################
# counter-only collections   #
##############################

class counters_coll :
    metadata: List[Tuple[int, int]]
    counters: Dict[Tuple[int, int], pd.DataFrame]

    def __init__(self, records) :
        self.metadata = []
        self.counters = {}

        for record in records :
            record_metadata = (record["rank"], record["id"])
            self.metadata.append(record_metadata)
            self.counters[record_metadata] = record["counters"]

    def _file_fillers (self, module_name: str):
        file_prefix = module_name + "_"
        file_suffix = ".parquet"
        return (file_prefix, file_suffix)

    def export_parquet(self, module_name: str, directory: str, prefix: str) :
        file_prefix, file_suffix = self._file_fillers(module_name)

        for record in self.metadata :
            file_id_prefix = "_".join(str(i) for i in record)
            counters_filename = file_prefix + prefix + "_" + file_id_prefix + "_counters" + file_suffix
            self.counters[record].to_parquet(os.path.join(directory, counters_filename))

class LUSTRE_coll(counters_coll) :
    metadata: List[Tuple[int, int]]
    counters: Dict[Tuple[int, int], pd.DataFrame]

    def __init__(self, records) :
        super().__init__(records)

    def export_parquet(self, directory: str, prefix: str) :
        super().export_parquet("LUSTRE", directory, prefix)

##############################
# counter + fcounter colls   #
##############################

class fcounters_coll(counters_coll) :
    fcounters: Dict[Tuple[int, int], pd.DataFrame]

    def __init__(self, records):
        # doesn't use super, might want to change it to use it but
        #   then we're looping over records twice and that's mildly annoying
        self.metadata = []
        self.counters = {}
        self.fcounters = {}

        for record in records :
            record_metadata = (record["rank"], record["id"])
            self.metadata.append(record_metadata)
            self.counters[record_metadata] = record["counters"]
            self.fcounters[record_metadata] = record["fcounters"]
    
    def export_parquet(self, module_name, directory, prefix):
        super().export_parquet(module_name, directory, prefix)
        file_prefix, file_suffix = super()._file_fillers(module_name)
        
        for record in self.metadata :
            file_id_prefix = "_".join(str(i) for i in record)
            fcounters_filename = file_prefix + prefix + "_" + file_id_prefix + "_fcounters" + file_suffix
            self.fcounters[record].to_parquet(os.path.join(directory, fcounters_filename))

class STDIO_coll(fcounters_coll) :
    def __init__(self, records) :
        super().__init__(records)

    def export_parquet(self, directory: str, prefix: str) :
        super().export_parquet("STDIO", directory, prefix)

class POSIX_coll(fcounters_coll) :
    def __init__(self, records) :
        super().__init__(records)

    def export_parquet(self, directory: str, prefix: str) :
        super().export_parquet("POSIX", directory, prefix)

#####################################################
# Main functions                                    #
#####################################################

def read_log(filename:str, debug:bool = False) -> List[Dict]:
    """Read the provided `.darshan` log file.
    
    Manually reads in the provided `.darshan` log file by loading in its
    core report data, then manually importing each module it sees.
    Importantly, it does not import any `DXT` modules or the `HEATMAP`
    module.

    This function skips the `DXT` modules because the use case it was
    developed in would seg fault on any attempt to read these modules.
    It skips the `HEATPMAP` module because the `pydarshan` package
    itself states: 
    ```
    Currently unsupported: HEATMAP in mod_read_all_records().
    ```
    """
    if debug :
        print("\tReading darshan log %s" % filename)
    
    if not os.path.exists(filename) :
        raise ValueError("Provided path %s does not exist." % filename)
    if not os.path.isfile(filename) :
        raise ValueError("Provided path %s is not a valid file." % filename)
    
    if debug :
        print("\tFile exists. Moving on...")

    output: Dict = {}
    with darshan.DarshanReport(filename, read_all=False) as report :
        if debug :
            print("File successfully opened as a report.")

        # Get metadata
        output["metadata"] = report.metadata

        # Get list of modules
        expected_modules = ["POSIX", "LUSTRE", "STDIO", "DXT_POSIX", "HEATMAP", "MPI-IO", "DXT_MPIIO"]
        modules = list(report.modules.keys())
        output["modules"] = modules
        
        if debug :
            print("\tFound modules: %s" % ",".join(modules))

        for m in modules :
            if m not in expected_modules :
                print("unexpected module found: %s" % m)

        loaded_modules = []

        # Get data for each found module
        if "POSIX" in modules :
            report.mod_read_all_records("POSIX",dtype="pandas")
            output["POSIX_coll"] = POSIX_coll(report.records["POSIX"])
            loaded_modules.append("POSIX_coll")
        
        if "LUSTRE" in modules :
            report.mod_read_all_lustre_records(dtype="pandas")
            output["LUSTRE_coll"] = LUSTRE_coll(report.records["LUSTRE"])
            loaded_modules.append("LUSTRE_coll")

        if "STDIO" in modules :
            report.mod_read_all_records("STDIO", dtype="pandas")
            output["STDIO_coll"] = STDIO_coll(report.records["STDIO"])
            loaded_modules.append("STDIO_coll")

        # DXT_POSIX causes a kernel crash _only in amal's data_.
        # TODO : make sure this works with pandas as an export type
        if "DXT_POSIX" in modules :
            # note that this generates a list of dictionaries, which then contain dataframes inside them
            report.mod_read_all_dxt_records("DXT_POSIX")
            pos = report.records['DXT_POSIX'].to_df()

            # created a custom output object to deal with it
            output["DXT_POSIX_coll_object"] = DXT_POSIX_coll(pos)
            loaded_modules.append("DXT_POSIX_coll_object")

        # Received message: Skipping. Currently unsupported: HEATMAP in mod_read_all_records().
        # if "HEATMAP" in modules :
        #     report.mod_read_all_records("HEATMAP", dtype="numpy")
        #     output["HEATMAP"] = report.records["HEATMAP"].to_df()

        if "MPI-IO" in modules :
            report.mod_read_all_records("MPI-IO", dtype="pandas")
            print("############### MPI IO ###############")
            print(report.records["MPI-IO"])

        if "DXT_MPIIO" in modules :
            report.mod_read_all_dxt_records("DXT_MPIIO", dtype="pandas")
            print("############### DXT MPI IO ###############")
            print(report.records["DXT_MPIIO"])
    
    output["report"] = report
    output["loaded_modules"] = loaded_modules

    return output

def collect_logfiles(directory:str, debug:bool = False) -> List[str]:
    """Collects all the `.darshan` log files in the provided directory.

    Collects all the `.darshan` log files in the provided direction,
    specifically only filtering to `.darshan` files, not
    `.darshan_partial`.
    """
    if not os.path.exists(directory) :
        raise ValueError("Provided path %s does not exist." % directory)
    
    if not os.path.isdir(directory) :
        raise ValueError("Provided path %s is not a directroy." % directory)
    
    if debug :
        print("\tPath %s has been found and confirmed a directory. Moving on..." % directory)

    # collect all the files in the provided directory; filter to only `.darshan` log files.
    files: List[str] = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    logfiles: List[str] = [f for f in files if os.path.splitext(f)[1] == ".darshan"]

    if debug :
        print("\tFound %i .darshan log files." % len(logfiles))

    return logfiles

def move_metadata_into_dataframe(report_data: Dict[str, Dict], debug: bool = False) -> pd.DataFrame:
    """Collects metadata from a list of reports and returns a dataframe.

    Gathers the data available in the `metadata` attribute of a darshan
    log for all of the darshan logs provided and collects them into a
    dataframe for storage.
    """

    # Names are taken from the 'metadata' attribute of the darshan report.
    mdf_header: List[str] = [
        "run_time",
        "start_time_nsec", # not sure why both nsec & sec
        "start_time_sec",
        "end_time_nsec",
        "end_time_sec",
        "jobid",
        "uid",
        "log_ver", # ?
        "metadata", # ?
        "nprocs",
        "exe"
    ]

    # Create dataframe to store metadata.
    metadata_df: pd.DataFrame = pd.DataFrame(columns=mdf_header)

    for report_name in list(report_data.keys()) :
        report = report_data[report_name]
        # Gather metadata and put into an array.
        
        values = [] # no type hint bc type varies
        # exe is under 'metadata' directly not 'job' so we can't do it
        #   as part of the for loop.
        for val in mdf_header[:-1] : 
            values.append(report['metadata']['job'][val])
        values.append(report['metadata']['exe'])

        # Make sure names aren't being duplicated.
        if report_name in metadata_df.index.values.tolist() :
            raise ValueError("The name %s is not unique -- attempted to insert a row into the metadata df into a location that already exists!" % report_name)
        
        # Add to dataframe.
        metadata_df.loc[report_name] = values
    
    if debug : print(metadata_df)

    # Return dataframe containing all report metadata.
    return(metadata_df)

def generate_name_for_report(report: Dict, debug=False) -> str:
    '''Generates a name for a given report using its uid and jobid metadata.
    '''
    job_metadata = report['metadata']['job']

    return "_".join([
        str(job_metadata['uid']), 
        str(job_metadata['jobid'])
        ])

def write_to_parquet(report_data: Dict[str, Dict], 
                     metadata_df: pd.DataFrame, 
                     output_dir: str, debug: bool = False) -> None:
    
    if os.path.exists(output_dir) and not os.path.isdir(output_dir) :
        raise ValueError("Provided directory %s exists and is not a directory. Aborting." % output_dir)

    elif os.path.exists(output_dir) :
        if debug : print("Path exists and is a directory. Proceeding.")

    elif not os.path.exists(output_dir) :
        if debug : print("Provided directory does not exist. Creating.")
        os.mkdir(output_dir)

    metadata_df_filename = os.path.join(output_dir, "metadata.parquet")
    metadata_df.to_parquet(metadata_df_filename)

    if debug: print("Metadata df written to %s." % metadata_df_filename)

    for report_name in list(report_data.keys()) :
        # report_base_name = os.path.join(output_dir, report_name)

        report: Dict = report_data[report_name]

        #module_names: List[str] = report['fetched_modules']
        #print(report["POSIX"])
        loaded_modules: List[str] = report["loaded_modules"]

        for module_name in loaded_modules :
            # filename:str = "_".join([report_base_name, module_name])
            # filename += '.parquet'
            # print("\tWriting %s module data to %s..." % (module_name, filename))
            # report[module_name].to_parquet(filename)
            report[module_name].export_parquet(output_dir, report_name)

        # for module_name in report['report'].records :
        #     module_filename:str = os.path.join(report_base_name, module_name)
        #     module_filename += ".parquet"

        #     if debug: print("\tWriting %s module data to %s..." % (module_name, module_filename))
        #     module_data: pd.DataFrame = report['report'].records[module_name][0]
        #     print(module_data)
        #     print(module_data.keys())
        #     print(module_data['counters'].keys())
        #     print(module_data['fcounters'].keys())
        #     module_data.to_parquet(module_filename)

    if debug: print("Done writing parquet files!")

def aggregate_darshan(directory:str, output_loc:str, debug:bool = False) :
    '''Runs the darshan log aggregation process.

    Collects the list of all `.darshan` files present in the provided
    directory and reads what data is available. Then compiles all of
    their data into a new `pandas.DataFrame` and ... TODO
    '''
    files: List[str] = collect_logfiles(directory, debug)
    collected_report_data: Dict[str, Dict] = {}

    if debug : print("Beginning to collect log data...")

    for f in files :
        tmp_report_data = read_log(os.path.join(directory, f), debug=debug)
        tmp_name = generate_name_for_report(tmp_report_data, debug)
        collected_report_data[tmp_name] = tmp_report_data
    
    if debug : print("Done collecting data!")

    if debug : print("Collecting metadata into a dataframe...")

    metadata_df: pd.DataFrame = move_metadata_into_dataframe(collected_report_data, debug)

    if debug : print("Done collecting metadata!")

    write_to_parquet(collected_report_data, metadata_df, output_loc, debug)

    # TODO : perform some statistics.
    #           e.g. how many of each type of module is present
    #           size ranges of data stored

    # TODO : output in some format
    
    # write_to_json(output_loc, collected_report_data, debug)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory",
                        help="Relative directory containing the darshan logs to parse and aggregate.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="If true, prints additional debug messages during runtime.")
    parser.add_argument("--output", default="parquet/",
                        help="Where to write the JSON dump of the aggregated DARSHAN logs.")
    args = parser.parse_args()

    aggregate_darshan(args.directory, args.output, args.debug)
