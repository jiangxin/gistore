require 'gistore/error'

module Gistore
  class Runner
    map ["ci", "backup"] => :commit
    desc "commit [-m <message>]", "Start commit changes (i.e. backup)"
    option :message, :aliases => :m, :desc => "commit log"
    def commit(*args)
      gistore = Repo.new(options[:repo] || ".")
      puts "debug: start to commit #{options[:repo] || "."}"

      # Check if backup needs rotate
      gistore.backup_rotate

      # Compare with last backup, and remove unwanted from cache
      latest_backups = gistore.get_backups
      last_backups = gistore.get_last_backups
      if last_backups
        last_backups.each do |entry|
          if entry and not latest_backups.include? entry
            cmds = [git_cmd,
                    "rm",
                    "--cached",
                    "-r",
                    "-f",
                    "--ignore-unmatch",
                    "--quiet",
                    "--",
                    entry.sub(/^\/+/, '')]
            cmds << {:check_return => false, :without_work_tree => true}
            gistore.shellout(*cmds)
          end
        end
      end

      # Add/remove files...
      latest_backups.each do |entry|
        # entry may be ignored by ".gitignore" under parent dirs.
        gistore.shellout git_cmd, "add", "-f", entry.sub(/^\/+/, '')
      end

      cmds = [git_cmd, "add", "-A"]
      cmds << ":/" if git_version_compare('1.7.6') >= 0
      gistore.shellout *cmds

      # Read status
      git_status = []
      gistore.shellout git_cmd, "status", "--porcelain" do |stdout|
        stdout.readlines.each do |line|
          line.strip!
          git_status << line unless line.empty?
        end
      end

      # Add contents of a submodule, not add as a submodule
      submodules = gistore.remove_submodules
      until submodules.empty? do
          puts "Re-add files in submodules: #{submodules.join(', ')}"
          submodules.each do |submod|
              git_status += gistore.add_submodule(submod)
          end
          # new add directories may contain other submodule.
          submodules = gistore.remove_submodules
      end

      # Format commit messages
      message = ""
      message << options[:message].strip if options[:message]
      message << "\n\n" unless message.empty?
      message << commit_summary(git_status)
      msgfile = File.join(gistore.repo_path, "COMMIT_EDITMSG")
      open(msgfile, "w") do |io|
        io.puts message  
      end

      # Start to commit
      committed = nil
      output = ""
      begin
        gistore.shellout(git_cmd, "commit", "-s", "--quiet", "-F", msgfile,
                         :without_locale => true,
                         :check_return => true) do |stdout|
          output = stdout.read
        end
        committed = true
      rescue CommandReturnError
        if output and
           (output =~ /no changes added to commit/ or
            output =~ /nothing to commit/)
          committed = false
        else
          raise
        end
      end

      # Save backups
      gistore.update_gistore_config(:backups => latest_backups)
      gistore.save_gistore_config

      display_name = gistore.task_name ?
                     "#{gistore.task_name} (#{gistore.repo_path})" :
                     "#{gistore.repo_path}"

      if committed
        puts "Successfully backup repo: #{display_name}"
      else
        puts "Nothing changed for repo: #{display_name}"
      end

      # Run git-gc
      gistore.git_gc

    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end

    map ["ci_all", "ci-all", "backup_all", "backup-all"] => :commit_all
    desc "commit-all [-m <message>]", "Start backup (commit) all tasks", :hide => true
    option :message, :aliases => :m, :desc => "commit log"
    def commit_all
      Gistore::get_gistore_tasks.each do |task, path|
        cmds = ["commit", "--repo", path]
        if options[:message]
          cmds << "-m"
          cmds << options[:message]
        end
        # invoke run only once? -- invoke :commit, args, opts
        Gistore::Runner.start(cmds)
      end
    end

  private
    def commit_summary(git_status)
      sample = 2
      statistics = {}
      output = []
      git_status.each do |line|
        k,v = line.split(" ", 2)
        statistics[k] ||= []
        statistics[k] << v
      end
  
      total = git_status.size
      detail = statistics.to_a.map{|h| "#{h[0]}: #{h[1].size}"}.sort.join(", ")
      output << "Backup #{total} item#{total > 1 ? "s" : ""} (#{detail})"
      output << ""
      statistics.keys.sort.each do |k|
        buffer = []
        if statistics[k].size > sample
          step = statistics[k].size / sample
          (0...sample).each do |i|
            buffer << statistics[k][step * i]
          end
          buffer << "...#{statistics[k].size - sample} more..."
        else
          buffer = statistics[k]
        end
        output << "  #{k} => #{buffer.join(", ")}"
      end
      output.join("\n")
    end
  end
end
