import os
import re

from fnmatch import fnmatch
from conans import ConanFile, CMake, tools

class VTKConan(ConanFile):
    name = "vtk" # DO NOT SUBMIT!! Should it stay lowercase or be uppercase?
    version = "9.0.1"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://vtk.org/"
    license = "MIT"
    description = "Visualization Toolkit by Kitware"
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    revision_mode = "scm"
    exports = ["LICENSE.md", "CMakeLists.txt", "FindVTK.cmake", "patches/**"]
    source_subfolder = "source_subfolder"
    options = {"shared": [True, False], "qt": [True, False], "mpi": [True, False],
                "fPIC": [True, False], "minimal": [True, False], "ioxml": [True, False],
                "ioexport": [True, False], "mpi_minimal": [True, False]}
    default_options = ("shared=False", "qt=False", "mpi=False", "fPIC=False",
                "minimal=False", "ioxml=False", "ioexport=False", "mpi_minimal=False")
    topics = ("conan", "VTK") # DO NOT SUBMIT!!!  Need suplementation like "3D graphics" and more ("Para View"?)

    version_split = version.split('.')
    short_version = "{}.{}".format(version_split[0], version_split[1])

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename("{}-{}".format(self.name, self.version), self.source_subfolder)

    def requirements(self):
        if self.options.qt:
            self.requires("qt/5.15.1@bincrafters/stable")
            self.options["qt"].shared = True
            if tools.os_info.is_linux:
                self.options["qt"].qtx11extras = True

    def _system_package_architecture(self):
        if tools.os_info.with_apt:
            if self.settings.arch == "x86":
                return ':i386'
            elif self.settings.arch == "x86_64":
                return ':amd64'

        if tools.os_info.with_yum:
            if self.settings.arch == "x86":
                return '.i686'
            elif self.settings.arch == 'x86_64':
                return '.x86_64'
        return ""

    def build_requirements(self):
        pack_names = None
        if not self.options.minimal and tools.os_info.is_linux:
            if tools.os_info.with_apt:
                pack_names = [
                    "freeglut3-dev",
                    "mesa-common-dev",
                    "mesa-utils-extra",
                    "libgl1-mesa-dev",
                    "libglapi-mesa",
                    "libsm-dev",
                    "libx11-dev",
                    "libxext-dev",
                    "libxt-dev",
                    "libglu1-mesa-dev"]

        if pack_names:
            installer = tools.SystemPackageTool()
            for item in pack_names:
                installer.install(item + self._system_package_architecture())

    def config_options(self):
        if self.settings.compiler == "Visual Studio":
            del self.options.fPIC

    def build(self):
        for patch in self.conan_data["patches"][self.version]:
            tools.patch(**patch)

        cmake = CMake(self)
        cmake.definitions["BUILD_TESTING"] = "OFF"
        cmake.definitions["BUILD_EXAMPLES"] = "OFF"
        cmake.definitions["BUILD_SHARED_LIBS"] = self.options.shared

        if self.options.minimal:
            cmake.definitions["VTK_Group_StandAlone"] = "OFF"
            cmake.definitions["VTK_Group_Rendering"] = "OFF"
        if self.options.ioxml:
            cmake.definitions["Module_vtkIOXML"] = "ON"
        if self.options.ioexport:
            cmake.definitions["Module_vtkIOExport"] = "ON"
        if self.options.qt:
            cmake.definitions["VTK_Group_Qt"] = "ON"
            cmake.definitions["VTK_QT_VERSION"] = "5"
            cmake.definitions["VTK_BUILD_QT_DESIGNER_PLUGIN"] = "OFF"
        if self.options.mpi:
            cmake.definitions["VTK_Group_MPI"] = "ON"
            cmake.definitions["Module_vtkIOParallelXML"] = "ON"
        if self.options.mpi_minimal:
            cmake.definitions["Module_vtkIOParallelXML"] = "ON"
            cmake.definitions["Module_vtkParallelMPI"] = "ON"

        if self.settings.build_type == "Debug" and self.settings.compiler == "Visual Studio":
            cmake.definitions["CMAKE_DEBUG_POSTFIX"] = "_d"

        if self.settings.os == 'Macos':
            self.env['DYLD_LIBRARY_PATH'] = os.path.join(self.build_folder, 'lib')
            self.output.info("cmake build: %s" % self.build_folder)

        cmake.configure(build_folder='build')
        if self.settings.os == 'Macos':
            # run_environment does not work here because it appends path just from
            # requirements, not from this package itself
            # https://docs.conan.io/en/latest/reference/build_helpers/run_environment.html#runenvironment
            lib_path = os.path.join(self.build_folder, 'lib')
            self.run('DYLD_LIBRARY_PATH={0} cmake --build build {1} -j'.format(lib_path, cmake.build_config))
        else:
            cmake.build()
        cmake.install()

    # From https://git.ircad.fr/conan/conan-vtk/blob/stable/8.2.0-r1/conanfile.py
    def cmake_fix_path(self, file_path, package_name):
        try:
            tools.replace_in_file(
                file_path,
                self.deps_cpp_info[package_name].rootpath.replace('\\', '/'),
                "${CONAN_" + package_name.upper() + "_ROOT}",
                strict=False
            )
        except:
            self.output.info("Ignoring {0}...".format(package_name))

    def cmake_fix_macos_sdk_path(self, file_path):
        # Read in the file
        with open(file_path, 'r') as file:
            file_data = file.read()

        if file_data:
            # Replace the target string
            file_data = re.sub(
                # Match sdk path
                r';/Applications/Xcode\.app/Contents/Developer/Platforms/MacOSX\.platform/Developer/SDKs/MacOSX\d\d\.\d\d\.sdk/usr/include',
                '',
                file_data,
                re.M
            )

            # Write the file out again
            with open(file_path, 'w') as file:
                file.write(file_data)

    def package(self):
        for path, subdirs, names in os.walk(os.path.join(self.package_folder, 'lib', 'cmake')):
            for name in names:
                if fnmatch(name, '*.cmake'):
                    cmake_file = os.path.join(path, name)

                    # if self.options.external_tiff:
                        # self.cmake_fix_path(cmake_file, "libtiff")
                    # if self.options.external_zlib:
                        # self.cmake_fix_path(cmake_file, "zlib")

                    if tools.os_info.is_macos:
                        self.cmake_fix_macos_sdk_path(cmake_file)

    def package_info(self):
        # For static linking in GCC libraries must be provided in appropriate order.
        # I couldn't find what is correct order of VTK libraries.
        # ${CONAN_LIBS} in VTK 7.1 has following order, which not necessary is correct, but it was used as starting point
        # ${CONAN_LIBS} = ['vtkCommonColor', 'vtkCommonCore', 'vtksys', 'vtkCommonDataModel', 'vtkCommonMath', 'vtkCommonMisc', 'vtkCommonSystem', 'vtkCommonTransforms', 'vtkCommonComputationalGeometry', 'vtkCommonExecutionModel', 'vtkDICOMParser', 'vtkFiltersCore', 'vtkFiltersExtraction', 'vtkFiltersGeneral', 'vtkFiltersStatistics', 'vtkImagingFourier', 'vtkImagingCore', 'vtkalglib', 'vtkFiltersGeometry', 'vtkFiltersHybrid', 'vtkImagingSources', 'vtkRenderingCore', 'vtkFiltersSources', 'vtkFiltersModeling', 'vtkIOCore', 'vtkzlib', 'vtkIOExport', 'vtkIOImage', 'vtkmetaio', 'vtkjpeg', 'vtkpng', 'vtktiff', 'vtkRenderingGL2PSOpenGL2', 'vtkRenderingOpenGL2', 'vtkglew', 'vtkgl2ps', 'vtkIOGeometry', 'vtkIOLegacy', 'vtkIOXML', 'vtkIOXMLParser', 'vtkexpat', 'vtkImagingColor', 'vtkImagingGeneral', 'vtkImagingHybrid', 'vtkImagingMath', 'vtkInteractionStyle', 'vtkInteractionWidgets', 'vtkRenderingAnnotation', 'vtkRenderingFreeType', 'vtkfreetype', 'vtkRenderingVolume', 'vtkRenderingContext2D', 'vtkRenderingContextOpenGL2', 'vtkRenderingVolumeOpenGL2', 'vtkViewsContext2D', 'vtkViewsCore']
        libs = tools.collect_libs(self)
        libs_ordered = []
        print('VTK libs before sort: ' + (';'.join(libs)))
        order = ['vtkViewsCore', 'vtkViewsContext2D', 'vtkRenderingVolumeOpenGL2', 'vtkRenderingContextOpenGL2', 'vtkRenderingContext2D', 'vtkRenderingVolume', 'vtkfreetype', 'vtkRenderingFreeType', 'vtkRenderingAnnotation', 'vtkInteractionWidgets', 'vtkInteractionStyle', 'vtkImagingMath', 'vtkImagingHybrid', 'vtkImagingGeneral', 'vtkImagingColor', 'vtkexpat', 'vtkIOXMLParser', 'vtkIOXML', 'vtkIOLegacy', 'vtkIOGeometry', 'vtkgl2ps', 'vtkglew', 'vtkRenderingOpenGL2', 'vtkRenderingGL2PSOpenGL2', 'vtktiff', 'vtkpng', 'vtkjpeg', 'vtkmetaio', 'vtkIOImage', 'vtkIOExport', 'vtkzlib', 'vtkIOCore', 'vtkFiltersModeling', 'vtkFiltersSources', 'vtkRenderingCore', 'vtkImagingSources', 'vtkFiltersHybrid', 'vtkFiltersGeometry', 'vtkalglib', 'vtkImagingCore', 'vtkImagingFourier', 'vtkFiltersStatistics', 'vtkFiltersGeneral', 'vtkFiltersExtraction', 'vtkFiltersCore', 'vtkDICOMParser', 'vtkCommonExecutionModel', 'vtkCommonComputationalGeometry', 'vtkCommonDataModel', 'vtkCommonSystem', 'vtkCommonTransforms', 'vtkCommonMath', 'vtkCommonMisc', 'vtkCommonCore', 'vtkCommonColor', 'vtksys']
        for item in order:
            for idx in range(len(libs)): 
                if item.lower() in libs[idx].lower():
                    value = libs.pop(idx)
                    libs_ordered.append(value)
                    break
        libs_ordered = libs + libs_ordered # add unordered elements, if any
        print('VTK libs ordered: ' + (';'.join(libs_ordered)))
        self.cpp_info.libs = libs_ordered

        # Adding system libs without 'lib' prefix and '.so' or '.so.X' suffix.
        if self.settings.os == 'Linux':
            self.cpp_info.system_libs.append('pthread')
            self.cpp_info.system_libs.append('dl')            # 'libvtksys-7.1.a' require 'dlclose', 'dlopen', 'dlsym' and 'dlerror' which on CentOS are in 'dl' library
            
        if not self.options.shared and self.options.qt:
            if self.settings.os == 'Windows':
                self.cpp_info.system_libs.append('Ws2_32')    # 'vtksys-9.0d.lib' require 'gethostbyname', 'gethostname', 'WSAStartup' and 'WSACleanup' which are in 'Ws2_32.lib' library
                self.cpp_info.system_libs.append('Psapi')     # 'vtksys-9.0d.lib' require 'GetProcessMemoryInfo' which is in 'Psapi.lib' library
                self.cpp_info.system_libs.append('dbghelp')   # 'vtksys-9.0d.lib' require '__imp_SymGetLineFromAddr64', '__imp_SymInitialize' and '__imp_SymFromAddr' which are in 'dbghelp.lib' library

            if self.settings.os == 'Macos':
                self.cpp_info.frameworks.extend(["CoreFoundation"]) # 'libvtkRenderingOpenGL2-9.0.a' require '_CFRelease', '_CFRetain', '_objc_msgSend' and much more which are in 'CoreFoundation' library
                self.cpp_info.frameworks.extend(["Cocoa"])          # 'libvtkRenderingOpenGL2-9.0.a' require '_CGWarpMouseCursorPosition' and more, 'libvtkRenderingUI-9.0.a' require '_OBJC_CLASS_$_NSApplication' and more, which are in 'Cocoa' library

        self.cpp_info.includedirs = [
            "include/vtk-%s" % self.short_version,
            "include/vtk-%s/vtknetcdf/include" % self.short_version,
            "include/vtk-%s/vtknetcdfcpp" % self.short_version
        ]