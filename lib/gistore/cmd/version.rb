require 'gistore/version'

module Gistore
  class Runner
    map ["--version", "-v"] => :version
    desc "version", "Show Gistore version and/or repository format version", :hide => true
    def version(*args)
      parse_common_options
      _version = Gistore::VERSION
      Dir.chdir(GISTORE_REPOSITORY) do
        if Gistore.is_git_repo? ".git"
          Gistore.shellout(git_cmd, "describe", "--always", "--dirty") do |stdout|
            _version << " ("
            _version << stdout.read.strip
            _version << ")"
          end
        end
      end
      puts "Gistore version #{_version}"

      gistore = Repo.new(options[:repo]) rescue nil if options[:repo]
      if gistore
        puts "Repository format #{gistore.repo_version}"
      end
    end
  end
end
