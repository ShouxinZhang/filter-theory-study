#include "options.hpp"
#include <iostream>

int main(int argc,char** argv) {
  // 主干仅负责错误边界与分派, 模型和评估逻辑均在独立库中。
  try {
    Eigen::setNbThreads(1);
    app::Options options(argc,argv);
    if(options.command=="help"||options.command=="--help") { app::help();return 0; }
    if(options.command=="run")return app::run(options);
    return app::commands(options);
  } catch(const std::exception& e) { std::cerr<<"错误: "<<e.what()<<'\n';return 1; }
}
