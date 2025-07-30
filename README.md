# Flask Website Setup

## Setup Instructions

1. **Create and activate the conda environment:**
   ```bash
   conda create -n cbt3_web_env python=3.11 -y
   conda activate cbt3_web_env
   ```
2. **Install dependencies:**
   ```bash
   conda install flask -y
   ```
   Or, to use pip:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Flask app:**
   ```bash
   python app.py
   ```

The website will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/) 