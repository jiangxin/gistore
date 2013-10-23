require 'yaml'
require 'fileutils'
require 'gistore/utils'
require 'gistore/error'
require 'gistore/config'

module Gistore

  class Repo
    attr_reader :task_name, :repo_path, :gistore_config, :gistore_backups

    class <<self
      def initialized?(name)
        File.directory?("#{name}/objects") &&
        File.directory?("#{name}/refs") &&
        File.exist?("#{name}/config")
      end

      def init(name, options = {})
        if File.directory? name and Dir.entries(name).size != 2
          raise "Non-empty directory '#{name}' is already exist."
        else
          FileUtils.mkdir_p name
        end

        # git initial --bare #{name}
        ENV['GIT_TEMPLATE_DIR'] = File.join(File.dirname(__FILE__), 'templates')
        # git-init can not take path as argument for git < v1.6.5
        Dir.chdir(name) do
          Gistore::shellout git_cmd, 'init',  '--bare', :without_work_tree => true
        end

        gistore = Repo.new(name)

        # Save repo version to "info/VERSION"
        gistore.repo_version = Gistore::REPO_VERSION

        # Set git config
        gistore.git_config('--plan', options[:plan] || 'normal')

        # Set gistore config
        gistore.update_gistore_config("increment_backup_number" => 30,
                                      "full_backup_number" => 12)
        gistore.save_gistore_config
      end
    end

    def initialize(name)
      # Setup taskname
      gistore_tasks = Gistore::get_gistore_tasks
      if File.exist? name and
         File.exist? name and
         File.directory? name
        @repo_path = realpath(name)
        gistore_tasks.each do |t, p|
          if realpath(p) == @repo_path
            @task_name = t
            break
          end
        end
      elsif gistore_tasks.include? name and
            File.exist? gistore_tasks[name] and
            File.directory? gistore_tasks[name]
        @repo_path = realpath gistore_tasks[name]
        @task_name = name
      else
        raise InvalidRepoError.new("Can not find repo at \"#{name}\"")
      end

      raise InvalidRepoError.new("Not a valid git repo: #{@repo_path}") unless is_git_repo?

      @gistore_config_file = "#{@repo_path}/info/gistore_config.yml"
      @gistore_backups_file = "#{@repo_path}/info/gistore_backups.yml"
      @gistore_exclude_file = "#{@repo_path}/info/exclude"
      @gistore_version_file = "#{@repo_path}/info/VERSION"
      @work_tree = "/"

      parse_gistore_config

      # Generate new info/exclude file
      update_info
    end

    def normalize_entry(entry)
      unless entry.start_with? '/'
        $stderr.puts "Warning: entry not start with '/'"
        return nil
      end
      # Note: not support UNC names
      result = entry.gsub(/\/\/+/, '/')
      if ['/'].include? result
        $stderr.puts "Warning: ignore root entry!"
        return nil
      end
      result
    end

    def validate_entry(entry)
      return false unless entry
      entry_path = realpath(entry)
      if repo_path == entry_path or repo_path =~ /^#{entry_path}\//
        $stderr.puts "Gistore repo is a subdir of entry: #{entry_path}"
        return false
      elsif entry_path =~ /^#{repo_path}\//
        $stderr.puts "Entry is a subdir of gistore repo: #{repo_path}"
        return false
      else
        return true
      end
    end

    def add_entry(entry)
      if entry
        entry = File.expand_path(entry)
        entry = normalize_entry(entry)
      end
      if not entry
        $stderr.puts "Warning: entry is nil"
      elsif not validate_entry(entry)
        $stderr.puts "Warning: entry (#{entry}) is not valid."
      elsif @gistore_backups.include? entry
        $stderr.puts "Warning: entry (#{entry}) is already added."
      else
        puts "Add entry: #{entry}."
        @gistore_backups << entry
        entry
      end
    end

    def remove_entry(entry)
      if not entry
        $stderr.puts "Warning: entry is nil"
      else
        unless @gistore_backups.include? entry
          entry = File.expand_path(entry)
          entry = normalize_entry(entry)
        end
        if @gistore_backups.delete entry
          puts "Remove entry: #{entry}."
        else
          $stderr.puts "Entry (#{entry}) not in backup list, nothing removed."
        end
      end
    end

    def save_gistore_backups
      backups = []
      @gistore_backups.sort.each do |entry|
        next if not validate_entry(entry)
        if backups[-1] and entry.start_with? backups[-1]
          if (entry.end_with? '/' or
              backups[-1].size == entry.size or
              entry.charat(backups[-1].size) == '/')
            $stderr.puts "Remove \"#{entry}\", for it has been added as \"#{backups[-1]}\""
            next
          end
        end
        backups << entry
      end
      @gistore_backups = backups
      f = File.new("#{@gistore_backups_file}.lock", 'w')
      f.write(@gistore_backups.to_yaml)
      f.close
      File.rename("#{@gistore_backups_file}.lock", @gistore_backups_file)
    end

    def save_gistore_config
      File.open("#{@gistore_config_file}.lock", 'w') do |io|
        io.write(@gistore_config.to_yaml)
      end
      File.rename("#{@gistore_config_file}.lock", @gistore_config_file)
    end

    def update_gistore_config(options={})
      options.each do |k, v|
        @gistore_config[k.to_s] = v
      end
    end

    def git_config(*args)
      if Hash === args.last
        options = args.pop.dup
      else
        options = {}
      end
      if args.size == 2 and (args[0] == '--plan' or args[0] == "plan")
        git_config('core.quotepath', false)
        git_config('core.autocrlf', false)
        git_config('core.logAllRefUpdates', true)
        git_config('core.sharedRepository', 'group')
        git_config('core.bigFileThreshold', '2m')

        case args[1]
        when /no[-_]?gc/
          git_config('gc.auto', 0)
          git_config('core.compression', 0)
          git_config('core.loosecompression', 0)
          update_gistore_config("plan" => "no-gc")
        when /no[-_]?compress/
          git_config('--unset', 'gc.auto')
          git_config('core.compression', 0)
          git_config('core.loosecompression', 0)
          update_gistore_config("plan" => "no-compress")
        else
          git_config('--unset', 'gc.auto')
          git_config('--unset', 'core.compression')
          git_config('--unset', 'core.loosecompression')
          update_gistore_config("plan" => "normal")
        end
        save_gistore_config
      else
        k, v = args
        if args.size == 0
          puts Gistore.show_column gistore_config.to_a.map {|h| "#{h[0]} : #{h[1].inspect}"}
        elsif args.size <= 2 and gistore_config.include? k
          if args.size == 1
            puts gistore_config[k]
          elsif args.size == 2
            update_gistore_config(k => v)
            save_gistore_config
          end
        else
          # Unset non-exist variable return error 5.
          system(git_cmd, 'config', *args)
          if options[:check_return] and $? and $?.exitstatus != 0
            raise CommandExit.new($?.exitstatus)
          end
        end
      end
    end

    def generate_git_exclude
      return if uptodate? @gistore_exclude_file, @gistore_backups_file
      generate_git_exclude!
    end

    def generate_git_exclude!
      backups = get_backups
      hierarchies = []
      excludes = []

      backups.each do |entry|
        excludes << entry
        entries = entry.split(/\/+/)[1..-1].inject([]){|sum, e| sum << [sum[-1], e].join('/')}
        entries.each do |e|
          unless hierarchies.include? e
            hierarchies << e
          end
        end
      end
      File.open(@gistore_exclude_file, "w") do |f|
        f.puts "*"
        # No trailing "/", because entry maybe a symlink
        hierarchies.each do |entry|
          f.puts "!#{entry}"
        end
        # Two trailing "**" will backup all files include files under subdir.
        excludes.each do |entry|
          if Gistore.git_version_compare('1.8.2') >= 0
            f.puts "!#{entry}/**"
          else
            f.puts "!#{entry}/*"
          end
        end
      end
    end

    def get_backups
      backups = []
      @gistore_backups.each do |entry|
        entry = normalize_entry(entry)
        next unless entry
        next unless validate_entry(entry)
        backups << entry
        if File.exist?(entry)
          entry_real = realpath(entry)
          backups << entry_real if entry != entry_real
        end
      end
      backups
    end

    def get_last_backups
      gistore_config["backups"]
    end

    def update_info
      # Because real directories pointed by entries may change,
      # always generate info/exclude,
      generate_git_exclude!
    end

    def setup_environment(options={})
      if options[:without_work_tree]
        ENV.delete 'GIT_WORK_TREE'
      else
        ENV['GIT_WORK_TREE'] = "."
      end
      if options[:without_grafts]
        ENV['GIT_GRAFT_FILE'] = "/dev/null"
      else
        ENV.delete 'GIT_GRAFT_FILE'
      end
      if options[:without_locale]
        ENV['LC_ALL'] = 'C'
      else
        ENV.delete 'LC_ALL'
      end
      unless options[:with_git_config]
        ENV.delete 'GIT_CONFIG'
      end
      unless options[:without_gitdir]
        ENV['GIT_DIR'] = repo_path
      end
      ENV.delete 'HOME'
      ENV.delete 'XDG_CONFIG_HOME'
      ENV['GIT_CONFIG_NOSYSTEM'] = '1'
      ENV['GIT_AUTHOR_NAME'] = get_login
      ENV['GIT_AUTHOR_EMAIL'] = get_email
      ENV['GIT_COMMITTER_NAME'] = get_login
      ENV['GIT_COMMITTER_EMAIL'] = get_email
    end

    # block has only 1 arg: stdout
    def shellout(*cmd, &block)
      if Hash === cmd.last
        options = cmd.last.dup
      else
        options = {}
      end
      setup_environment(options)
      if options[:without_work_tree]
        Gistore::shellout(*cmd, &block)
      else
        Dir.chdir(options[:work_tree] || @work_tree) do
          Gistore::shellout(*cmd, &block)
        end
      end
    end

    # block has 3 args: stdin, stdout, stderr
    def shellpipe(*cmd, &block)
      if Hash === cmd.last
        options = cmd.last.dup
      else
        options = {}
      end
      setup_environment(options)
      if options[:without_work_tree]
        Gistore::shellpipe(*cmd, &block)
      else
        Dir.chdir(options[:work_tree] || @work_tree) do
          Gistore::shellpipe(*cmd, &block)
        end
      end
    end

    def system(*args)
      if Hash === args.last
        options = args.pop.dup
      else
        options = {}
      end
      setup_environment(options)
      if options[:without_work_tree]
        # Kernel system can not convert bool, int to string
        Kernel::system(*args.map{|e| e.to_s})
      else
        Dir.chdir(options[:work_tree] || @work_tree) do
          # Kernel system can not convert bool, int to string
          Kernel::system(*args.map{|e| e.to_s})
        end
      end
    end

    def repo_version
      File.open(@gistore_version_file, "r") do |io|
        io.read.to_s.strip
      end
    end

    def repo_version=(ver)
      File.open(@gistore_version_file, "w") do |io|
        io.puts ver
      end
    end

    def remove_submodules
      submodules = []
      shellpipe(git_cmd, "submodule", "status",
                :without_locale => true,
                :check_return => false) do |ignore, stdout, stderr|
        stdout.readlines.each do |line|
          line.strip!
          if line =~ /.\w{40} (\w*) (.*)?/
            submodules << Regexp.last_match(1)
          end
        end
        stderr.readlines.each do |line|
          line.strip!
          if line =~ /No submodule mapping found in .gitmodules for path '(.*)'/
            submodules << Regexp.last_match(1)
          end
        end
      end
      if submodules.empty?
        []
      else
        puts "Remove submodules: #{submodules.join(", ")}"
        system(git_cmd, "rm", "-f", "--cached", "-q", *submodules)
        submodules
      end
    end

    # add submodule as normal directory
    def add_submodule(submodule, status=[])
      # add tmp file in submodule
      tmpfile = File.join(submodule, '.gistore-submodule')
      File.open(File.join(@work_tree, tmpfile), 'w') {}

      # git add tmp file in submodule
      shellout(git_cmd, "add", "-f", tmpfile)

      # git add whole submodule dir (-f to bypass .gitignore in parent dir)
      shellout(git_cmd, "add", "-f", submodule)

      # git rm -f tmp file in submodule
      shellout(git_cmd, "rm", "-f", tmpfile)

      # Read status
      shellout git_cmd, "status", "--porcelain", "--", submodule do |stdout|
        stdout.readlines.each do |line|
          line.strip!
          status << line unless line.empty?
        end
      end
      status
    end

    def backup_rotate
      increment_backup_number = gistore_config["increment_backup_number"].to_i
      full_backup_number = gistore_config["full_backup_number"].to_i
      return if full_backup_number == 0 and increment_backup_number == 0
      increment_backup_number = 30 if increment_backup_number < 1
      full_backup_number = 6 if full_backup_number < 1

      count = shellout(git_cmd, "rev-list", "master",
                       :without_grafts => true,
                       :check_return => false){|stdout| stdout.readlines.size}.to_i
      if count <= increment_backup_number
          puts "No backup rotate needed. #{count} <= #{increment_backup_number}"
          return
      else
          puts "Debug: start to rotate branch, because #{count} > #{increment_backup_number}"
      end

      # list branches with prefix: gistore/
      branches = []
      cmds  = [git_cmd, "branch"]
      cmds += ["--list", "gistore/*"] if Gistore.git_version_compare('1.7.8') >= 0
      shellout *cmds do |stdout|
        stdout.readlines.each do |line|
          line.strip!
          branches << line if line =~ /^gistore\//
        end
      end
      branches.sort!

      # Remove unwanted branches
      if branches.size >= full_backup_number and full_backup_number > 0
        until branches.size <= full_backup_number
          right = branches.pop
          shellout git_cmd, "branch", "-D", right
          puts "Debug: deleted unwanted branch - #{right}"
        end
      end

      # Add new branch to branches
      if branches.size < full_backup_number
        if branches.empty?
          branches << "gistore/1"
        else
          branches << branches[-1].succ
        end
      end

      # Rotate branches
      branches_dup = branches.dup
      right = nil
      until branches_dup.empty? do
        left = branches_dup.pop
        if left and right
          # shellout git_cmd, "update-ref", "refs/heads/#{right}", "refs/heads/#{left}"
          shellout git_cmd, "branch", "-f", right, left
          puts "Debug: update branch #{right} (value from #{left})"
        end
        right = left
      end

      # Save master to gistore/1
      old_branch = "master"
      new_branch = branches[0] || "gistore/1"
      shellout git_cmd, "branch", "-f", new_branch, old_branch
      puts "Debug: update branch #{new_branch} (from master)"

      # Run: git cat-file commit master | \
      #          sed  '/^parent/ d'     | \
      #          git hash-object -t commit -w --stdin
      cobj = ""
      shellout git_cmd, "cat-file", "commit", "master" do |stdout|
        end_of_header = false
        stdout.readlines.each do |line|
          if line !~ /^parent [0-9a-f]{40}\s*$/ or end_of_header
            cobj << line
          end
          if line == "\n" and not end_of_header
            cobj << <<-EDIT_COMMIT_LOG
Full backup of #{task_name || File.basename(repo_path)}

#{Gistore.show_column gistore_backups}

** Copy from this commit **

            EDIT_COMMIT_LOG
            end_of_header = true
          end
        end
      end

      object_id = shellpipe(git_cmd, "hash-object",
                            "-t", "commit",
                            "-w", "--stdin") do |stdin, stdout, stderr|
                    stdin.puts cobj
                    stdin.close
                    stdout.read
                  end.to_s.strip

      raise "Bad object_id created by 'git hash-object'" if object_id !~ /^[0-9a-f]{40}$/
      shellout git_cmd, "update-ref", "refs/heads/master", object_id
      puts "Debut: update master with #{object_id}"

      # create file .git/info/grafts.
      #   parent of object_id -> gistore/N^
      #   paretn of gistore/N last commit -> gistore/(N-1)^
      grafts_file = File.join(repo_path, "info", "grafts")
      grafts = [object_id]

      branches.each do |branch|
        shellout(git_cmd, "rev-list", "refs/heads/#{branch}",
                 :without_grafts => true) do |stdout|
          lines = stdout.readlines
          # lines[0] and object_id points to same tree.
          new = lines.size > 1 ? lines[1] : lines[0]
          old = lines[-1]
          grafts << new.strip
          grafts << old.strip
        end
      end
      File.open(grafts_file, "w") do |io|
        until grafts.empty?
          left = grafts.shift
          right = grafts.shift
          if left and right
            io.puts "#{left} #{right}"
          end
        end
      end
    end

    def git_gc(*args)
      if Hash === args.last
        options = args.pop.dup
      else
        options = {}
      end
      gc_enabled = true
      shellout git_cmd, "config", "gc.auto" do |stdout|
        if stdout.read.strip == "0"
          gc_enabled = false
        end
      end
      if gc_enabled
        if options[:force]
          system git_cmd, "reflog", "expire", "--expire=now", "--all", :without_work_tree => true
          system git_cmd, "prune", "--expire=now", :without_work_tree => true
          args.delete "--auto" if args.include? "--auto"
          args << {:without_work_tree => true}
          system git_cmd, "gc", *args
        else
          args.unshift "--auto" unless args.include? "--auto"
          args << {:without_work_tree => true}
          system git_cmd, "gc", *args
        end
      else
        $stderr.puts "GC is disabled."
      end
    end

  private
    def is_git_repo?
      self.class.initialized?(repo_path)
    end

    def load_default_config
      @gistore_config = DEFAULT_GISTORE_CONFIG
      gistore_default_config_file = File.join(File.dirname(File.dirname(File.dirname(__FILE__))),
                                              "config/gistore.yml")
      @gistore_config.merge!(YAML::load_file(gistore_default_config_file) || {})
      @gistore_backups = []
    end

    def parse_gistore_config
      load_default_config
      if File.exist? @gistore_config_file
        @gistore_config.merge!(YAML::load_file(@gistore_config_file))
      end
      if File.exist? @gistore_backups_file
        @gistore_backups = YAML::load_file(@gistore_backups_file)
      end
    end

    def realpath(entry)
      if File.exist? entry
        if File.respond_to? :realpath
          File.realpath(entry)
        else
          # ruby 1.8
          require 'pathname'
          Pathname.new(entry).realpath.to_s
        end
      else
        File.expand_path(entry)
      end
    end

    def uptodate?(file, *depends)
      if File.exist?(file) and FileUtils::uptodate?(file, depends)
        true
      else
        false
      end
    end

    def get_login
      username = gistore_config["username"]
      username = `#{git_cmd} config user.name`.strip if username.nil? or username.empty?
      if username.nil? or username.empty?
        require 'etc'
        username = Etc::getlogin
      end
      username
    end

    def get_email
      useremail = gistore_config["useremail"]
      useremail = `#{git_cmd} config user.email`.strip if useremail.nil? or useremail.empty?
      useremail = "none" if useremail.nil? or useremail.empty?
      useremail
    end
  end
end
