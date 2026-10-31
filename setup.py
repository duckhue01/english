from setuptools import setup, find_packages

setup(
    name="speakflow",
    version="1.0.0",
    description="Terminal voice recording studio for English pronunciation coaching with Google NotebookLM",
    author="SpeakFlow Team",
    packages=find_packages(),
    install_requires=[
        "sounddevice>=0.5.0",
        "soundfile>=0.12.0",
        "numpy>=1.20.0",
        "rich>=13.0.0",
        "questionary>=2.0.0",
        "eng_to_ipa>=0.0.2",
        "pronouncing>=0.3.0",
    ],
    entry_points={
        "console_scripts": [
            "speakflow=speakflow.cli:main",
        ],
    },
    python_requires=">=3.9",
)
