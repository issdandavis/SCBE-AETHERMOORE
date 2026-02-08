# https://foss.heptapod.net/pypy/cffi/-/issues/441
# https://github.com/pypa/setuptools/issues/1040

from pathlib import Path
import platform
from setuptools import setup
import sys
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

# Pending https://hpyproject.org/
ABI3_EXCLUDE_IMPLEMENTATIONS = {
	'PyPy',  # https://github.com/orgs/pypy/discussions/4884#discussioncomment-8309845
}


class site_bdist_wheel(_bdist_wheel):
	"""https://github.com/joerick/python-ctypes-package-sample/blob/7db688cd6ee32ae95bce0f75fb7d806926e20252/setup.py#L29"""

	def finalize_options(self):
		# https://github.com/pypa/wheel/blob/0.42.0/src/wheel/bdist_wheel.py#L244
		if (
			platform.python_implementation() not in ABI3_EXCLUDE_IMPLEMENTATIONS
			# https://github.com/pypa/wheel/blob/0.42.0/src/wheel/bdist_wheel.py#L267
			and (
				self.distribution.has_ext_modules()
				or self.distribution.has_c_libraries()
			)
			# https://github.com/pypa/setuptools/blob/v69.0.3/setuptools/command/build_ext.py#L160
			and all(ext.py_limited_api for ext in self.distribution.ext_modules)
		):
			self.py_limited_api = (
				f'cp{sys.version_info.major}{sys.version_info.minor}'
				if platform.python_implementation() == 'CPython'
				else f'py{sys.version_info.major}{sys.version_info.minor}'
			)
		super().finalize_options()

	def get_tag(self):
		python, abi, plat = _bdist_wheel.get_tag(self)
		if (
			self.py_limited_api
			and platform.python_implementation() not in ABI3_EXCLUDE_IMPLEMENTATIONS
		):
			# https://github.com/pypa/cibuildwheel/blob/v2.16.3/cibuildwheel/util.py#L653
			python = (
				f'cp{sys.version_info.major}{sys.version_info.minor}'
				if platform.python_implementation() == 'CPython'
				else f'py{sys.version_info.major}{sys.version_info.minor}'
			)
			abi = f'abi{sys.version_info.major}'
		return python, abi, plat


setup(
	cmdclass={'bdist_wheel': site_bdist_wheel},
	cffi_modules=[f'{p!s}:ffi' for p in Path('cffi_modules').glob('[!_]*.py')],
)
