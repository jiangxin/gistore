module Gistore
  class Runner
    map "config" => :cmd_config
    desc "config name value", "Read or update gistore config or git config"
    option :plan, :desc => "builtin plan: no-gc, no-compress, or normal (default)"
    def cmd_config(*args)
      gistore = Repo.new(options[:repo] || ".")
      if options[:plan]
        return gistore.git_config('--plan', options[:plan])
      end

      args << {:check_return => true}
      gistore.git_config(*args)
    rescue CommandExit => e
      exit e.message.to_i
    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end
  end
end

