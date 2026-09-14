#pragma once
#include "pf/io.hpp"
#include "pf/noise.hpp"

namespace pf {
struct Observations { int id=0; std::vector<double> values; };
struct PublicDataset {
  std::string environment,variant,parameters,hash;
  std::vector<Observations> trajectories;
};
struct TruthTrajectory { int id=0; Vector initial; Matrix states; };
struct TruthDataset {
  std::string environment,variant,observation_hash;
  std::vector<TruthTrajectory> trajectories;
};
void save_dataset(const fs::path& directory,PublicDataset& data,const TruthDataset& truth,std::uint64_t seed);
PublicDataset load_observations(const fs::path& directory);
TruthDataset load_truth(const fs::path& directory);
void generate_dataset(const fs::path& directory,const std::string& environment,
                      const std::string& variant,int trajectories,std::uint64_t seed,const EnvironmentNoise& noise={});
} // namespace pf
