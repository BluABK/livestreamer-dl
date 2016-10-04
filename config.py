import configparser
import os


class Config:
    config = configparser.RawConfigParser()

    def __init__(self):
        """
        Config class
        Loads configuration file 'config.ini'
        If none is found one will be generated
        :return:
        """
        #config_file = os.getcwd() + os.sep + "config.ini"
        config_file = 'config.ini'
        self.config.read(config_file)
        print(config_file)
        print(self.get_untitled_name())
        try:
            self.config.read(config_file)
        except IOError:
            # Create config file if none exists FIXME: Doesn't create a file
            self.config.add_section('general')
            self.add_comment('general', 'The location you want your downloads saved to')
            self.config.set('general', 'path', '')
            self.add_comment('general', 'The filename given to untitled downloads')
            self.config.set('general', 'untitled_name', 'untitled')
            # Save changes
            with open(config_file, 'wb') as new_config:
                self.config.write(new_config)
            #self.config.write(newfile)
            #newfile.close()
            # Read config
            self.config.read(config_file)
            """
            try:
                self.config.read(config_file)
            except IOError:
                # If it fails the second time, something is probably wrong with the environment
                raise
            """
    def add_comment(self, section, comment):
        self.config.set(section, '; ' + comment, '')

    def test_section(self, section):
        if self.config.has_section(section) is False:
            self.config.add_section(section)

    def test_option(self, section, option, default=''):
        self.test_section(section)
        if self.config.has_option(section, option) is False:
            self.config.set(section, option, default)

    def get_path(self):
        self.test_option('general', 'path', '')
        return str(self.config.get('general', 'path'))

    def get_untitled_name(self):
        self.test_option('general', 'untitled_name', default='untitled')
        return str(self.config.get('general', 'untitled_name'))
