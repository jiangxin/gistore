module Gistore
  class Runner
    desc "rm <path> ...", "Remove entry from backup list"
    def rm(*args)
      parse_common_options_and_repo
      raise "nothing to remove." if args.empty?
      args.each do |entry|
        gistore.remove_entry entry
      end
      gistore.save_gistore_backups
    rescue Exception => e
      Tty.die "#{e.message}"
    end
  end
end
