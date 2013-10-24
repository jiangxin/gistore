module Gistore
  class Runner
    desc "gc [--force]", "Run git-gc if gc.auto != 0"
    option :force, :type => :boolean, :aliases => [:f], :desc => "run git-gc without --auto option"
    def gc(*args)
      parse_common_options_and_repo
      opts = options.dup
      opts.delete :repo
      args << opts
      gistore.git_gc(*args)
    rescue Exception => e
      Tty.die "#{e.message}"
    end
  end
end
