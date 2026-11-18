class Spyglass < Formula
  include Language::Python::Virtualenv

  desc "Keep selected Apple Containers up to date"
  homepage "https://github.com/wolfpaulus/spyglass"
  url "https://files.pythonhosted.org/packages/ed/56/bab4b729d393babe11ab513ff2dd0f222621df0bbc99c89172b1acf097ce/apple_container_spyglass-1.0.tar.gz"
  sha256 "994dec31724181cff1f4bf3c4068f11ccd4b3e71c0752ec6f2ef7da5c02f7d0b"
  license "MIT"

  depends_on "python@3.15"

  def install
    virtualenv_install_with_resources
  end

  service do
    run [opt_bin/"spyglass"]
    run_at_load true
    run_type :interval
    interval 3600
    environment_variables PATH: std_service_path_env
  end

  test do
    fake_container = testpath/"container"
    fake_container.write <<~EOS
      #!/bin/sh
      echo '[]'
    EOS
    fake_container.chmod 0755

    ENV["HOME"] = testpath.to_s
    ENV.prepend_path "PATH", testpath
    system bin/"spyglass"
  end
end
