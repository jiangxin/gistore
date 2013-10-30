require 'gistore/version'

module Gistore
  class Runner
    map ["--version", "-v"] => :version
    desc "version", "Show Gistore version and/or repository format version", :hide => true
    def version(*args)
      parse_common_options
      v = Gistore::VERSION
      Dir.chdir(GISTORE_REPOSITORY) do
        if Gistore.is_git_repo? ".git"
          Gistore.shellout(git_cmd, "describe", "--always", "--dirty") do |stdout|
            v = stdout.read.strip
            v.sub!(/^v/, '')
            v << " (#{Gistore::VERSION})" if v != Gistore::VERSION
          end
        end
      end
      puts "Gistore version #{v}"

      gistore = Repo.new(options[:repo]) rescue nil if options[:repo]
      if gistore
        puts "Repository format #{gistore.repo_version}"
      end
    end
  end
end
