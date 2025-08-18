import tkinter as tk
from tkinter import ttk, filedialog
from cdisc_rules_engine.models.validation_args import Validation_args
from scripts.run_validation import run_validation
import sys
import io
import os
from datetime import datetime
from cdisc_rules_engine.enums.report_types import ReportTypes
from cdisc_rules_engine.enums.progress_parameter_options import ProgressParameterOptions
from cdisc_rules_engine.enums.default_file_paths import DefaultFilePaths
from cdisc_rules_engine.models.external_dictionaries_container import (
    ExternalDictionariesContainer,
    DictionaryTypes,
)
import threading
import click
from core import update_cache, list_rules, list_rule_sets, list_ct


@click.group()
def cli():
    pass


cli.add_command(update_cache)
cli.add_command(list_rules)
cli.add_command(list_rule_sets)
cli.add_command(list_ct)


class ValidationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CDISC Rules Engine")

        # Create a notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Create frames for each tab
        self.validation_frame = ttk.Frame(self.notebook, padding="10")
        self.cache_frame = ttk.Frame(self.notebook, padding="10")
        self.listing_frame = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.validation_frame, text="Validation")
        self.notebook.add(self.cache_frame, text="Cache Management")
        self.notebook.add(self.listing_frame, text="Listing")

        # Create a frame for the output text area
        self.output_frame = ttk.Frame(self.root, padding="10")
        self.output_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.create_validation_widgets()
        self.create_cache_widgets()
        self.create_listing_widgets()
        self.create_output_widgets()

    def create_validation_widgets(self):
        # Create and place the input widgets
        self.widgets = {}
        row = 0

        # Function to create a label and an entry with a browse button
        def create_browse_entry(parent, label_text, row, is_directory=False):
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(parent, width=50)
            entry.grid(row=row, column=1, sticky="ew")
            button = ttk.Button(
                parent,
                text="Browse...",
                command=lambda: self.browse(entry, is_directory),
            )
            button.grid(row=row, column=2, sticky="w")
            return entry

        # Function to create a label and an entry
        def create_entry(parent, label_text, row, default_text=""):
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(parent, width=50)
            entry.grid(row=row, column=1, columnspan=2, sticky="ew")
            entry.insert(0, default_text)
            return entry

        # Function to create a label and a combobox
        def create_combobox(parent, label_text, row, values, default_value):
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w")
            combobox = ttk.Combobox(parent, values=values, width=47)
            combobox.grid(row=row, column=1, columnspan=2, sticky="ew")
            combobox.set(default_value)
            return combobox

        # Function to create a label and a checkbutton
        def create_checkbutton(parent, label_text, row):
            var = tk.BooleanVar()
            checkbutton = ttk.Checkbutton(parent, variable=var, text=label_text)
            checkbutton.grid(row=row, column=0, columnspan=3, sticky="w")
            return var

        # Standard and Version
        self.widgets["standard"] = create_entry(self.validation_frame, "Standard:", row)
        row += 1
        self.widgets["version"] = create_entry(self.validation_frame, "Version:", row)
        row += 1
        self.widgets["substandard"] = create_entry(self.validation_frame, "Substandard:", row)
        row += 1

        # Data Paths
        self.widgets["data"] = create_browse_entry(self.validation_frame, "Data Directory:", row, is_directory=True)
        row += 1
        self.widgets["dataset_path"] = create_browse_entry(self.validation_frame, "Dataset Path:", row)
        row += 1

        # Output
        self.widgets["output"] = create_browse_entry(self.validation_frame, "Output File:", row)
        row += 1
        self.widgets["output_format"] = create_combobox(
            self.validation_frame, "Output Format:", row, ReportTypes.values(), ReportTypes.XLSX.value
        )
        row += 1
        self.widgets["raw_report"] = create_checkbutton(self.validation_frame, "Raw Report", row)
        row += 1

        # Cache and Logging
        self.widgets["cache"] = create_entry(self.validation_frame, "Cache Path:", row, DefaultFilePaths.CACHE.value)
        row += 1
        self.widgets["log_level"] = create_combobox(
            self.validation_frame, "Log Level:", row, ["info", "debug", "error", "critical", "disabled", "warn"], "info"
        )
        row += 1

        # Other options
        self.widgets["report_template"] = create_browse_entry(self.validation_frame, "Report Template:", row)
        row += 1
        self.widgets["controlled_terminology_package"] = create_entry(self.validation_frame, "Controlled Terminology Package:", row)
        row += 1
        self.widgets["define_version"] = create_entry(self.validation_frame, "Define-XML Version:", row)
        row += 1
        self.widgets["define_xml_path"] = create_browse_entry(self.validation_frame, "Define-XML Path:", row)
        row += 1
        self.widgets["whodrug"] = create_browse_entry(self.validation_frame, "WHODrug Path:", row, is_directory=True)
        row += 1
        self.widgets["meddra"] = create_browse_entry(self.validation_frame, "MedDRA Path:", row, is_directory=True)
        row += 1
        self.widgets["loinc"] = create_browse_entry(self.validation_frame, "LOINC Path:", row, is_directory=True)
        row += 1
        self.widgets["medrt"] = create_browse_entry(self.validation_frame, "MEDRT Path:", row, is_directory=True)
        row += 1
        self.widgets["unii"] = create_browse_entry(self.validation_frame, "UNII Path:", row, is_directory=True)
        row += 1
        self.widgets["snomed_version"] = create_entry(self.validation_frame, "SNOMED Version:", row)
        row += 1
        self.widgets["snomed_edition"] = create_entry(self.validation_frame, "SNOMED Edition:", row)
        row += 1
        self.widgets["snomed_url"] = create_entry(self.validation_frame, "SNOMED URL:", row, "https://snowstorm.snomedtools.org/snowstorm/snomed-ct/")
        row += 1
        self.widgets["rules"] = create_entry(self.validation_frame, "Rules (comma-separated):", row)
        row += 1
        self.widgets["local_rules"] = create_browse_entry(self.validation_frame, "Local Rules Path:", row, is_directory=True)
        row += 1
        self.widgets["custom_standard"] = create_checkbutton(self.validation_frame, "Custom Standard", row)
        row += 1
        self.widgets["progress"] = create_combobox(
            self.validation_frame, "Progress:", row, ProgressParameterOptions.values(), ProgressParameterOptions.BAR.value
        )
        row += 1
        self.widgets["validate_xml"] = create_checkbutton(self.validation_frame, "Validate XML", row)
        row += 1

        # Create the "Run Validation" button
        self.run_button = ttk.Button(self.validation_frame, text="Run Validation", command=self.start_validation_thread)
        self.run_button.grid(row=row, column=0, columnspan=3, pady="10")
        row += 1

    def create_cache_widgets(self):
        # API Key
        ttk.Label(self.cache_frame, text="CDISC Library API Key:").grid(row=0, column=0, sticky="w")
        self.api_key_entry = ttk.Entry(self.cache_frame, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky="ew")

        # Update Cache Button
        self.update_cache_button = ttk.Button(self.cache_frame, text="Update Cache", command=self.start_update_cache_thread)
        self.update_cache_button.grid(row=1, column=0, columnspan=2, pady="10")

    def create_listing_widgets(self):
        # Create a notebook for the listing sub-tabs
        listing_notebook = ttk.Notebook(self.listing_frame)
        listing_notebook.pack(expand=True, fill="both")

        list_rules_frame = ttk.Frame(listing_notebook, padding="10")
        list_rule_sets_frame = ttk.Frame(listing_notebook, padding="10")
        list_ct_frame = ttk.Frame(listing_notebook, padding="10")

        listing_notebook.add(list_rules_frame, text="List Rules")
        listing_notebook.add(list_rule_sets_frame, text="List Rule Sets")
        listing_notebook.add(list_ct_frame, text="List CT")

        # List Rules widgets
        self.list_rules_widgets = {}
        row = 0
        self.list_rules_widgets["standard"] = ttk.Entry(list_rules_frame, width=50)
        ttk.Label(list_rules_frame, text="Standard:").grid(row=row, column=0, sticky="w")
        self.list_rules_widgets["standard"].grid(row=row, column=1, sticky="ew")
        row += 1
        self.list_rules_widgets["version"] = ttk.Entry(list_rules_frame, width=50)
        ttk.Label(list_rules_frame, text="Version:").grid(row=row, column=0, sticky="w")
        self.list_rules_widgets["version"].grid(row=row, column=1, sticky="ew")
        row += 1
        self.list_rules_widgets["custom_rules"] = tk.BooleanVar()
        ttk.Checkbutton(list_rules_frame, text="Custom Rules", variable=self.list_rules_widgets["custom_rules"]).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Button(list_rules_frame, text="List Rules", command=self.start_list_rules_thread).grid(row=row, column=0, columnspan=2, pady="10")

        # List Rule Sets widgets
        self.list_rule_sets_widgets = {}
        row = 0
        self.list_rule_sets_widgets["custom"] = tk.BooleanVar()
        ttk.Checkbutton(list_rule_sets_frame, text="Custom Rule Sets", variable=self.list_rule_sets_widgets["custom"]).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Button(list_rule_sets_frame, text="List Rule Sets", command=self.start_list_rule_sets_thread).grid(row=row, column=0, columnspan=2, pady="10")

        # List CT widgets
        self.list_ct_widgets = {}
        row = 0
        self.list_ct_widgets["subsets"] = ttk.Entry(list_ct_frame, width=50)
        ttk.Label(list_ct_frame, text="Subsets (comma-separated):").grid(row=row, column=0, sticky="w")
        self.list_ct_widgets["subsets"].grid(row=row, column=1, sticky="ew")
        row += 1
        ttk.Button(list_ct_frame, text="List CT", command=self.start_list_ct_thread).grid(row=row, column=0, columnspan=2, pady="10")


    def create_output_widgets(self):
        # Create the output text area
        self.output_text = tk.Text(self.output_frame, wrap=tk.WORD, height=20)
        self.output_text.pack(expand=True, fill="both")

    def browse(self, entry_widget, is_directory=False):
        if is_directory:
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename()
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def start_validation_thread(self):
        # Disable the run button to prevent multiple validations at once
        self.run_button.config(state=tk.DISABLED)
        # Run the validation in a separate thread to keep the GUI responsive
        validation_thread = threading.Thread(target=self.run_validation)
        validation_thread.start()

    def start_update_cache_thread(self):
        # Disable the button
        self.update_cache_button.config(state=tk.DISABLED)
        # Run in a separate thread
        update_cache_thread = threading.Thread(target=self.run_update_cache)
        update_cache_thread.start()

    def start_list_rules_thread(self):
        list_rules_thread = threading.Thread(target=self.run_list_rules)
        list_rules_thread.start()

    def start_list_rule_sets_thread(self):
        list_rule_sets_thread = threading.Thread(target=self.run_list_rule_sets)
        list_rule_sets_thread.start()

    def start_list_ct_thread(self):
        list_ct_thread = threading.Thread(target=self.run_list_ct)
        list_ct_thread.start()


    def run_update_cache(self):
        self.run_cli_command(update_cache, ['--apikey', self.api_key_entry.get()])

    def run_list_rules(self):
        args = []
        if self.list_rules_widgets["standard"].get():
            args.extend(['-s', self.list_rules_widgets["standard"].get()])
        if self.list_rules_widgets["version"].get():
            args.extend(['-v', self.list_rules_widgets["version"].get()])
        if self.list_rules_widgets["custom_rules"].get():
            args.append('--custom_rules')
        self.run_cli_command(list_rules, args)

    def run_list_rule_sets(self):
        args = []
        if self.list_rule_sets_widgets["custom"].get():
            args.append('--custom')
        self.run_cli_command(list_rule_sets, args)

    def run_list_ct(self):
        args = []
        if self.list_ct_widgets["subsets"].get():
            args.extend(['-s', self.list_ct_widgets["subsets"].get()])
        self.run_cli_command(list_ct, args)

    def run_cli_command(self, command, args):
        # Clear the output text area
        self.output_text.delete("1.0", tk.END)

        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = sys.stderr = TextRedirector(self.output_text)

        try:
            from click.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(command, args, catch_exceptions=False)
            if result.output:
                 self.output_text.insert(tk.END, result.output)

        except Exception as e:
            self.output_text.insert(tk.END, f"An error occurred: {e}\n")
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def run_validation(self):
        # Clear the output text area
        self.output_text.delete("1.0", tk.END)

        # Redirect stdout and stderr to the output text area
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = sys.stderr = self.output_text_redirector = TextRedirector(self.output_text)

        try:
            # Get values from the widgets
            standard = self.widgets["standard"].get()
            version = self.widgets["version"].get()
            substandard = self.widgets["substandard"].get()
            data = self.widgets["data"].get()
            dataset_path = self.widgets["dataset_path"].get()
            output = self.widgets["output"].get()
            output_format = self.widgets["output_format"].get()
            raw_report = self.widgets["raw_report"].get()
            cache_path = self.widgets["cache"].get()
            log_level = self.widgets["log_level"].get()
            report_template = self.widgets["report_template"].get()
            ct_package = self.widgets["controlled_terminology_package"].get()
            define_version = self.widgets["define_version"].get()
            define_xml_path = self.widgets["define_xml_path"].get()
            whodrug = self.widgets["whodrug"].get()
            meddra = self.widgets["meddra"].get()
            loinc = self.widgets["loinc"].get()
            medrt = self.widgets["medrt"].get()
            unii = self.widgets["unii"].get()
            snomed_version = self.widgets["snomed_version"].get()
            snomed_edition = self.widgets["snomed_edition"].get()
            snomed_url = self.widgets["snomed_url"].get()
            rules = self.widgets["rules"].get().split(",") if self.widgets["rules"].get() else []
            local_rules = self.widgets["local_rules"].get()
            custom_standard = self.widgets["custom_standard"].get()
            progress = self.widgets["progress"].get()
            validate_xml = self.widgets["validate_xml"].get()

            # Construct dataset paths
            if data:
                dataset_paths = [os.path.join(data, fn) for fn in os.listdir(data)]
            elif dataset_path:
                dataset_paths = [dataset_path]
            else:
                self.output_text.insert(tk.END, "Error: You must provide either a data directory or a dataset path.\n")
                return

            # Construct external dictionaries
            external_dictionaries = ExternalDictionariesContainer(
                {
                    DictionaryTypes.UNII.value: unii,
                    DictionaryTypes.MEDRT.value: medrt,
                    DictionaryTypes.MEDDRA.value: meddra,
                    DictionaryTypes.WHODRUG.value: whodrug,
                    DictionaryTypes.LOINC.value: loinc,
                    DictionaryTypes.SNOMED.value: {
                        "edition": snomed_edition,
                        "version": snomed_version,
                        "base_url": snomed_url,
                    },
                }
            )

            # Create Validation_args object
            args = Validation_args(
                cache=cache_path,
                pool_size=4,  # Or get from a widget
                dataset_paths=dataset_paths,
                log_level=log_level,
                report_template=report_template,
                standard=standard,
                version=version,
                substandard=substandard,
                controlled_terminology_package=set(ct_package.split(",")) if ct_package else set(),
                output=output,
                output_format={output_format},
                raw_report=raw_report,
                define_version=define_version,
                external_dictionaries=external_dictionaries,
                rules=rules,
                local_rules=local_rules,
                custom_standard=custom_standard,
                progress=progress,
                define_xml_path=define_xml_path,
                validate_xml=validate_xml,
            )

            # Run the validation
            run_validation(args)

        except Exception as e:
            self.output_text.insert(tk.END, f"An error occurred: {e}\n")
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Re-enable the run button
            self.run_button.config(state=tk.NORMAL)


class TextRedirector(io.TextIOBase):
    def __init__(self, widget):
        self.widget = widget

    def write(self, s):
        self.widget.insert(tk.END, s)
        self.widget.see(tk.END)
        self.widget.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = ValidationApp(root)
    root.mainloop()
