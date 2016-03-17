from setuptools import setup, find_packages

setup(name='MusicPlayer',
      author='Sven Wiltink',
      version='0.0.1',
      packages=find_packages('src'),  # include all packages under src
      package_dir={'': 'src'},        # tell distutils packages are under src
      install_requires=[
            'pyspotify',
            'pyalsaaudio'
      ]
)
