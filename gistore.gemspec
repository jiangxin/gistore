# coding: utf-8
lib = File.expand_path('../lib', __FILE__)
$LOAD_PATH.unshift(lib) unless $LOAD_PATH.include?(lib)
require 'gistore/version'

Gem::Specification.new do |s|
  s.name          = "gistore"
  s.version       = Gistore::VERSION
  s.platform      = Gem::Platform::RUBY
  s.authors       = ["Jiang Xin"]
  s.email         = ["worldhello.net@gmail.com"]
  s.description   = "A backup utility using git as a backend."
  s.summary       = "Gistore-#{Gistore::VERSION}"
  s.homepage      = "https://github.com/jiangxin/gistore"
  s.license       = "GPL v2"

  s.files         = `git ls-files -- lib/`.split($/)
  s.files         += %w[README.md CHANGELOG COPYING]
  s.files.delete_if{ |f| f =~ %r{gistore/vendor/|gistore/cmd/update.rb} }
  s.bindir        = "exe"
  s.executables   = `git ls-files -- exe/`.split($/).map{ |f| File.basename(f) }
  s.test_files    = `git ls-files -- {spec,t}/*`.split($/)
  s.require_paths = ["lib"]

  s.add_development_dependency "bundler"
  s.add_development_dependency "rake"

  s.add_dependency "open4", "~> 1.3"
  s.add_dependency "thor", "~> 0.18"
end
