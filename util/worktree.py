import glob
import json
import os
import re
import configparser
from datetime import datetime
from moodle.fieldnames import JsonFieldNames as Jn

import math


class WorkTree:
    def __init__(self, init=False, force=False, skip_init=False):
        if skip_init:
            return

        self.root = self.get_work_tree_root()
        if self.root is None and not init:
            raise NotInWorkTree()

        if init:
            self.root = self._initialize(force)

        self.meta_root = self.root + '.mdt/'
        self.config = self.meta_root + 'config'
        self.user_meta = self.meta_root + 'users'
        self.sync_meta = self.meta_root + 'sync'
        self.moodle_meta = self.meta_root + 'moodle'
        self.course_meta = self.meta_root + 'courses'
        self.assignment_meta = self.meta_root + 'assignments/'
        self.submission_meta = self.meta_root + 'submissions/'
        self.grade_meta = self.meta_root + 'grades/'

        if not init:
            self._course_data = self._load_json_file(self.course_meta)
            self._user_data = self._load_json_file(self.user_meta)
            self._assignment_data = self._merge_json_data_in_folder(self.assignment_meta)
            self._submission_data = self._merge_json_data_in_folder(self.submission_meta)
            self._grade_data = self._merge_json_data_in_folder(self.grade_meta)

    @staticmethod
    def _initialize(force):
        try:
            os.makedirs('.mdt/assignments', exist_ok=force)
            os.makedirs('.mdt/submissions', exist_ok=force)
            os.makedirs('.mdt/grades', exist_ok=force)
            if force or not os.path.isfile('.mdt/users'):
                with open('.mdt/users', 'w') as users:
                    users.write('[]')
            if force or not os.path.isfile('.mdt/courses'):
                with open('.mdt/courses', 'w') as courses:
                    courses.write('[]')
            return os.getcwd() + '/'
        except FileExistsError:
            raise

    @property
    def global_config(self):
        if 'XDG_CONFIG_HOME' in os.environ:
            if os.path.isfile(os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'):
                return os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
        elif os.path.isfile(os.path.expanduser('~/.config/mdtconfig')):
            return os.path.expanduser('~/.config/mdtconfig')
        elif os.path.isfile(os.path.expanduser('~/.mdtconfig')):
            return os.path.expanduser('~/.mdtconfig')
        else:
            return self.create_global_config_file()

    @staticmethod
    def create_global_config_file():
        file = ''
        if 'XDG_CONFIG_HOME' in os.environ:
            if os.path.isdir(os.environ['XDG_CONFIG_HOME']):
                file = os.environ['XDG_CONFIG_HOME'] + '/mdtconfig'
        elif os.path.isdir(os.path.expanduser('~/.config')):
            file = os.path.expanduser('~/.config/mdtconfig')
        else:
            file = os.path.expanduser('~/.mdtconfig')
        text = 'could not find global config, creating {}'
        print(text.format(file))
        open(file, 'w').close()
        return file

    def get_config_file_list(self):
        global_config = self.global_config
        cfg_files = [global_config]
        work_tree = self.get_work_tree_root()
        if work_tree is not None:
            # default_config_files order is crucial: work_tree cfg overrides global
            cfg_files.append(work_tree + '/.mdt/config')
        return cfg_files

    @staticmethod
    def get_work_tree_root():
        """ determines the work tree root by looking at the .mdt folder in cwd or parent folders
        :returns the work tree root as String or None
        """
        cwd = os.getcwd()
        repo = None
        while not os.path.isdir('.mdt'):
            if '/' == os.getcwd():
                os.chdir(cwd)
                return None
            os.chdir(os.pardir)
        if os.path.isdir('.mdt'):
            repo = os.getcwd()
        os.chdir(cwd)
        return repo + '/'

    @property
    def in_root(self):
        return os.path.isdir('.mdt')

    @property
    def in_tree(self):
        return self.root is not None

    @property
    def data(self):
        courses = self.courses
        merged = []
        for course in courses:
            course[Jn.users] = self.users[str(course[Jn.id])]
            course_assignments = [a for a in self.assignments if a[Jn.course] == course[Jn.id]]

            for assignment in course_assignments:
                for submission in self.submissions:
                    if assignment[Jn.id] == submission[Jn.assignment_id]:
                        assignment[Jn.submissions] = submission[Jn.submissions]
                for grade in self.grades:
                    if assignment[Jn.id] == grade[Jn.assignment_id]:
                        assignment[Jn.grades] = grade[Jn.grades]
            course[Jn.assignments] = course_assignments

            merged.append(course)

        return merged

    @property
    def assignments(self):
        return self._assignment_data

    @property
    def submissions(self):
        return self._submission_data

    @property
    def courses(self):
        return self._course_data

    @property
    def grades(self):
        return self._grade_data

    @property
    def users(self):
        return self._user_data

    @staticmethod
    def _load_json_file(filename):
        try:
            with open(filename) as file:
                return json.load(file)
        except json.decoder.JSONDecodeError as e:
            print(e)
            pass

    @staticmethod
    def _write_config(path, data):
        with open(path, 'w') as file:
            file.write(data)

    @staticmethod
    def _write_meta(path, data):
        with open(path, 'w') as file:
            json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)

    def _merge_json_data_in_folder(self, path):
        files = glob.glob(path + '*')
        data_list = [self._load_json_file(file) for file in files]
        return data_list

    def write_global_config(self, config_dict):
        with open(self.global_config, 'w') as file:
            cfg_parser = configparser.ConfigParser()
            cfg_parser['global moodle settings'] = config_dict
            cfg_parser.write(file)

    def write_local_config(self, config_data):
        self._write_config(self.config, config_data)

    def update_local_assignment_meta(self, assignment):
        as_config_file = self.assignment_meta + str(assignment['id'])
        if os.path.isfile(as_config_file):
            with open(as_config_file, 'r') as local_file:
                local_as_config = json.load(local_file)
            if local_as_config[Jn.time_modified] < assignment[Jn.time_modified]:
                self._write_meta(as_config_file, assignment)
                return 'updated'
            else:
                return 'unchanged'
        else:
            self._write_meta(as_config_file, assignment)
            return 'new'

    def write_local_user_meta(self, users):
        self._write_meta(self.user_meta, users)

    def write_local_course_meta(self, course_data):
        self._write_meta(self.course_meta, course_data)

    def write_local_submission_meta(self, assignment):
        meta_file = self.submission_meta + str(assignment[Jn.assignment_id])
        if os.path.isfile(meta_file):
            self._write_meta(meta_file, assignment)
            return 'updated'
        else:
            self._write_meta(meta_file, assignment)
            return 'new'

    def write_local_grade_meta(self, assignment):
        g_config_file = self.grade_meta + str(assignment[Jn.assignment_id])
        self._write_meta(g_config_file, assignment)

    def write_submission_files(self, content, prefix):
        if len(content) == 1:
            prefix += '--'
            file, data = content[0]
            filename = prefix + file.path[1:].replace('/', '_')
            with open(filename, 'wb') as pulled_file:
                pulled_file.write(data)
            return

        for file, data in content:
            filename = prefix + file.path
            file_dir = os.path.dirname(filename)
            os.makedirs(file_dir, exist_ok=True)
            with open(filename, 'wb') as pulled_file:
                pulled_file.write(data)

    def read_sync_meta(self):
        try:
            return self._read_meta(self.sync_meta)
        except Exception as e:
            print(e)
            return {'last_sync': 0}

    @staticmethod
    def _read_meta(file):
        with open(file) as meta_file:
            return json.load(meta_file)

    def update_sync_meta(self):
        sync_meta = {
            'last_sync': math.floor(datetime.now().timestamp())
        }
        self._write_meta(self.sync_meta, sync_meta)

    @staticmethod
    def safe_file_name(name):
        return re.sub(r'\W', '_', name)

    def write_grading_and_html_file(self, assignment):
        grade_file_head = '{{"assignment_id": {:d}, "grades": [\n'
        grade_file_end = '\n]}'
        grade_line_format = '{{"name": "{}", "id": {:d}, "grade": 0.0, "feedback":"" }}'
        grade_file_content = []
        filename = 'gradingfile.json'
        #todo add known grades to grading file.
        if assignment.team_submission:
            for s in assignment.valid_submissions:
                group = assignment.course.groups[s.group_id]
                grade_file_content.append(grade_line_format.format(group.name, s.id))
        else:
            for s in assignment.valid_submissions:
                user = assignment.course.users[s.user_id]
                grade_file_content.append(grade_line_format.format(user.name, s.id))
        # checks for existing file and chooses new name, maybe merge data?
        if os.path.isfile(filename):
            new_name = 'gradingfile_{:02d}.json'
            i = 0
            filename = new_name.format(i)
            while os.path.isfile(filename):
                i += 1
                filename = new_name.format(i)
            print('grading file exists, writing to: {}'.format(filename))
        a_folder = self.safe_file_name('{}--{:d}'.format(assignment.name, assignment.id)) + '/'
        os.makedirs(a_folder, exist_ok=True)
        with open(a_folder + filename, 'w') as grading_file:
            grading_file.write(
                grade_file_head.format(assignment.id) +
                ',\n'.join(sorted(grade_file_content)) +
                grade_file_end
            )
        html = assignment.merged_html
        if html is not None:
            with open(a_folder + '00_merged_submissions.html', 'w') as merged_html:
                merged_html.write(html)

    def create_folders(self, files):
        folders = set([os.path.dirname(f.path) for f in files])
        for folder in folders:
            os.makedirs(folder, exist_ok=True)

    def write_submission_file(self, file, content):
        with open(file.path, 'wb') as fd:
            fd.write(content)

    def prepare_download(self, assignments):
        files = []
        for a in assignments:
            for s in a.submissions.values():
                a_folder = self.safe_file_name('{}--{:d}'.format(a.name, a.id))
                s_files = s.files
                if len(s_files) > 1:
                    s_folder = a_folder + '/' + self.safe_file_name(s.prefix)
                    for file in s_files:
                        file.path = s_folder + file.path
                        files.append(file)
                        # print(folder + file.path)
                elif len(s_files) == 1:
                    file = s_files[0]
                    path = a_folder + '/' + self.safe_file_name(s.prefix) + '--'
                    path += file.path[1:].replace('/', '_')
                    file.path = path
                    files.append(file)
        self.create_folders(files)
        return files


class NotInWorkTree(Exception):
    def __init__(self):
        self.message = 'You are not in an initialized work tree. Go get one.'

    def __str__(self):
        return self.message


class MetaDataFolder(dict):

    def __format__(self, *args, **kwargs):
        # https://www.python.org/dev/peps/pep-3101/
        return super().__format__(*args, **kwargs)

    def update(self, other=None, **kwargs):
        super().update(other, **kwargs)

    def clear(self):
        return super().clear()

    def popitem(self):
        return super().popitem()

    # todo does not reflect changes on side effects, always returns a copy
    def __init__(self, folder, **kwargs):
        super().__init__(**kwargs)
        self.folder = folder + '/'
        os.makedirs(folder, exist_ok=True)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError as ke:
            if default is not None:
                return default
            else:
                raise ke

    def copy(self):
        return {key: self.__getitem__(key) for key in self.keys()}

    def keys(self):
        return [int(filename) for filename in os.listdir(self.folder)]

    def items(self):
        return [(key, self.__getitem__(key)) for key in self.keys()]

    def pop(self, key, default=None):
        data = self.__getitem__(key)
        self.__delitem__(key)
        return data

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    # noinspection PyMethodOverriding
    def values(self):
        return [self.__getitem__(key) for key in self.keys()]

    def __len__(self):
        return len(self.keys())

    def __delitem__(self, key):
        try:
            os.remove(self.folder + key)
        except FileNotFoundError:
            raise KeyError(key)

    def __repr__(self, *args, **kwargs):
        return '<MetaDataFolder: {}>'.format(self.folder)

    def __getitem__(self, key):
        filename = self.folder + str(key)
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except IOError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        with open(self.folder + key, 'w') as file:
            file.write(value)

    def __contains__(self, *args, **kwargs):
        return os.path.isfile(self.folder + args[0])

    def __str__(self, *args, **kwargs):
        return self.folder