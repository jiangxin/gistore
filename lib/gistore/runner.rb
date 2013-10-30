require 'thor'
require 'gistore/error'

module Gistore
  class Runner < Thor
    attr_accessor :gistore
    # Use command name "gistore" in help instead of "gistore.rb"
    def self.basename; "gistore"; end

    # Show in help screen
    package_name "Gistore"

    class_option :repo, :banner => "<repo>", :desc => "path to gistore repo", :required => false
    class_option :help, :type => :boolean, :aliases => [:h], :desc => "Help", :required => false
    class_option :verbose, :type => :boolean, :aliases => [:v], :desc => "verbose", :required => false
    class_option :quiet, :type => :boolean, :aliases => [:q], :desc => "quiet", :required => false

  private
    def parse_common_options
      if options[:verbose]
        Tty.options[:verbose] = true
      elsif options[:quiet]
        Tty.options[:quiet] = true
      end
    end

    def parse_common_options_and_repo
      parse_common_options
      self.gistore = Repo.new(options[:repo] || ".")
    end

    def git_version_compare(version)
      Gistore::git_version_compare(version)
    end

    def git_cmd; Gistore::git_cmd; end

    def git_version; Gistore::git_version; end

    end
end

Dir["#{File.dirname(__FILE__)}/cmd/*.rb"].each {|file| require file}
