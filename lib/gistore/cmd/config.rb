module Gistore
  class Runner
    map "config" => :cmd_config
    desc "config name value", "Read or update gistore config or git config"
    option :plan, :desc => "builtin plan: no-gc, no-compress, or normal (default)"
    def cmd_config(*args)
      parse_common_options_and_repo
      if options[:plan]
        return gistore.git_config('--plan', options[:plan])
      end

      args << {:check_return => true}
      unless gistore.git_config(*args)
        exit 1
      end
    rescue SystemExit
      exit 1
    rescue Exception => e
      Tty.die "#{e.message}"
    end
  end
end

