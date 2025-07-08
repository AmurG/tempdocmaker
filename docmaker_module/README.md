# DocMaker Module

This directory contains the core execution logic for the `docmaker-minimal` pipeline.

## Usage

This module is designed to be run from the root directory of the `docmaker-minimal` project.

1.  **Ensure you are in the project's root directory.**
2.  **Make sure you have completed the setup** (Python virtual environment, `pip install`, and `.env` file creation) as described in the main `README.md`.
3.  **Execute the pipeline** by running the `run.sh` script:

```bash
./docmaker_module/run.sh
```

This script will call all the necessary Python scripts in the correct sequence to perform the end-to-end documentation generation process. 