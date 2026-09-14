#include "pf/dataset.hpp"
#include "pf/environment.hpp"

namespace pf {
void generate_dataset(const fs::path& directory,const std::string& name,const std::string& variant,
                      int count,std::uint64_t seed,const EnvironmentNoise& noise) {
  auto model=make_environment(name,noise);
  require(count>0&&count<=100000,"轨迹数必须在 1 到 100000 之间");
  require(variant=="fixed"||variant=="matched-prior","变体只能是 fixed 或 matched-prior");
  PublicDataset data;data.environment=model->name();data.variant=variant;data.parameters=model->parameters();
  TruthDataset truth;truth.environment=data.environment;truth.variant=variant;
  for(int id=0;id<count;++id) {
    Random initial(seed_for(seed,id,0)),process(seed_for(seed,id,1)),observation(seed_for(seed,id,2));
    Vector state(model->dimension()),next(model->dimension()),process_noise(model->process_noise().dimension());
    if(variant=="matched-prior")model->sample_initial(state,initial);
    else if(model->dimension()==1)state[0]=0.1;
    else state<<-0.05,0.001,0.7,-0.055;
    TruthTrajectory hidden;hidden.id=id;hidden.initial=state;hidden.states.resize(model->dimension(),model->steps());
    Observations observed;observed.id=id;observed.values.reserve(model->steps());
    for(int k=1;k<=model->steps();++k) {
      if(k>model->initial_time()) {
        model->process_noise().sample(process_noise,process);
        model->transition(k,state,process_noise,next);state.swap(next);
      }
      hidden.states.col(k-1)=state;
      observed.values.push_back(model->observe(state,observation));
    }
    data.trajectories.push_back(std::move(observed));truth.trajectories.push_back(std::move(hidden));
  }
  save_dataset(directory,data,truth,seed);
}
} // namespace pf
