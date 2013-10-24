module Gistore
  class Runner
    desc "restore-from-backups", "Export to a series of full/increment backups"
    option :from, :required => true, :desc => "path of backup packs", :banner => "<from>"
    option :to, :required => true, :desc => "path of repo.git to restore to", :banner => "<repo.git>"
    def restore_from_backups
      parse_common_options
      from = options[:from]
      repo_name = options[:to]
      backups = []
      if not File.exist? from
        raise "Path \"#{from}\" does not exist."
      elsif File.directory? from
        backups = Dir.glob("#{from}/*.pack")
      elsif from.end_with? ".pack"
        backups << from
      end

      if not backups or backups.empty?
        raise "Can not find valid pack file(s) from \"#{from}\""
      else
        backups = backups.map {|p| File.expand_path(p.strip)}
      end

      if not File.exist? repo_name
        Repo.init repo_name
      elsif not Gistore.is_git_repo? repo_name
        raise "Path \"#{repo_name}\" is not a valid repo, create one using \"gistore init\""
      end

      self.gistore = Repo.new(repo_name)
      output = ""
      backups.each do |pack|
        begin
          gistore.shellpipe(git_cmd, "unpack-objects", "-q",
                            :work_tree => gistore.repo_path,
                            :check_return => true
                           ) do |stdin, stdout, stderr|
            File.open(pack, "r") do |io|
              stdin.write io.read
            end
            stdin.close
            output << stdout.read
            output << "\n" unless output.empty?
            output << stderr.read
          end
        rescue
          Tty.warning "failed to unpack #{pack}"
        end
      end

      danglings = []
      cmds = [git_cmd, "fsck"]
      cmds << "--dangling" if Gistore.git_version_compare('1.7.10') >= 0
      gistore.shellout(*cmds) do |stdout|
        stdout.readlines.each do |line|
          if line =~ /^dangling commit (.*)/
            danglings << $1.strip
          end
        end
      end

      unless danglings.empty?
        begin
          gistore.shellout(git_cmd, "rev-parse", "master", :check_return => true)
        rescue
          if danglings.size == 1
            gistore.shellout(git_cmd, "update-ref", "refs/heads/master", danglings[0])
          else
            show_dangling_commits danglings
          end
        else
          show_dangling_commits danglings
        end
      end
    rescue Exception => e
      Tty.error "Failed to restore-from-backups.\n#{output}"
      Tty.die "#{e.message}"
    end

  private

    def show_dangling_commits(danglings)
      puts "Found dangling commits after restore backups:"
      puts "\n"
      puts Tty.show_columns danglings
      puts "\n"
      puts "You may like to update master branch with it(them) by hands."
    end
  end
end
