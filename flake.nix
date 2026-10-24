{
  description = "Traggo to Redmine integration";

  inputs = {
    nixpkgs = {
      url = "github:NixOS/nixpkgs/nixos-unstable";
    };
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    supportedSystems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    pkgsFor = system: nixpkgs.legacyPackages.${system};

    # python-redmine is not packaged in nixpkgs
    python-redmine = ps:
      ps.buildPythonPackage rec {
        pname = "python-redmine";
        version = "2.5.0";
        pyproject = true;
        src = ps.fetchPypi {
          inherit pname version;
          hash = "sha256-gb3FKarxiGWOLQdIgJbHldA9TiVnEb+j+j8Xse7MRxs=";
        };
        build-system = [ps.setuptools];
        dependencies = [ps.requests];
        pythonImportsCheck = ["redminelib"];
      };

    # The runtime dependencies from pyproject.toml, taken from nixpkgs
    dependencies = ps:
      [
        ps.pydantic
        ps.pydantic-settings
        ps.python-dotenv
        (python-redmine ps)
        ps.gql
        ps.more-itertools
        ps.pytz
        ps.sqlalchemy_1_4
      ]
      ++ ps.gql.optional-dependencies.requests;
  in {
    packages = forAllSystems (system: let
      ps = (pkgsFor system).python3Packages;
    in {
      thyme = ps.buildPythonApplication {
        pname = "thyme";
        version = "0.0.0";
        pyproject = true;
        src = ./.;
        build-system = [ps.poetry-core];
        dependencies = dependencies ps;
        # pyproject.toml has caret ranges (pytz ^2021.1, gql ^3.2.0) that
        # nixpkgs has moved past, use the versions nixpkgs ships instead.
        pythonRelaxDeps = true;
        pythonImportsCheck = ["thyme.app"];
      };
      default = self.packages.${system}.thyme;
    });

    devShells = forAllSystems (system: let
      pkgs = pkgsFor system;
    in {
      default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages dependencies)
          pkgs.poetry
        ];
      };
    });
  };
}
