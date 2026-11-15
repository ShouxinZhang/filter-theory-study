// Deterministic finite-volume Bayes filter in theta coordinates.
// x=sin^2(pi theta/2) conjugates f(x)=4x(1-x) to the tent map.
// No process noise or particle resampling. Grid refinement controls discretization.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
#include <omp.h>
#ifdef REFERENCE_LONG_DOUBLE
using Real=long double;
#else
using Real=double;
#endif
int main(int argc,char**argv){
 if(argc!=7)throw std::runtime_error("data.csv output.bin trials steps cells R");
 const int B=std::stoi(argv[3]),K=std::stoi(argv[4]),M=std::stoi(argv[5]);
 const Real R=Real(std::stod(argv[6])),pi=std::acos(Real(-1));
 if(M%2||M<16||R<=0)throw std::runtime_error("invalid parameters");
 std::vector<double> ys(B*K),results(B*K*2);
 std::vector<Real> xm(M),prior(M);
 std::ifstream in(argv[1]); std::string line;std::getline(in,line);int seen=0;
 while(std::getline(in,line)){
  std::replace(line.begin(),line.end(),',',' ');std::istringstream s(line);
  int b,k;double truth,y;s>>b>>k>>truth>>y;
  if(b>=B)break;
  if(k<=K){ys[b*K+k-1]=y;seen++;}
 }
 if(seen!=B*K)throw std::runtime_error("incomplete observations");
 auto psi=[&](Real t){return std::pow(std::sin(pi*t/2),2);};
 for(int j=0;j<M;j++){xm[j]=psi((j+Real(.5))/M);prior[j]=psi(Real(j+1)/M)-psi(Real(j)/M);}
 Real first_mean=0,initial_mean=0;
 for(int j=0;j<M;j++){
  initial_mean+=prior[j]*xm[j];
  first_mean+=.5*(prior[j/2]+prior[M-1-j/2])*xm[j];
 }
 if(std::abs(initial_mean-.5)>1e-12||std::abs(first_mean-2./3)>5./(M*M))
  throw std::runtime_error("analytic no-observation moments failed");
 #pragma omp parallel for schedule(dynamic)
 for(int b=0;b<B;b++){
  std::vector<Real> p=prior,next(M),logg(M);
  for(int k=0;k<K;k++){
   const Real y=ys[b*K+k];Real top=-INFINITY;
   for(int j=0;j<M;j++){Real d=y-xm[j]*xm[j];logg[j]=-.5*d*d/R;top=std::max(top,logg[j]);}
   Real z=0,mean=0,m2=0;
   for(int j=0;j<M;j++){
    next[j]=.5*(p[j/2]+p[M-1-j/2])*std::exp(logg[j]-top);z+=next[j];
   }
   for(int j=0;j<M;j++){next[j]/=z;mean+=next[j]*xm[j];m2+=next[j]*xm[j]*xm[j];}
   results[2*(b*K+k)]=mean;results[2*(b*K+k)+1]=std::max(Real(0),m2-mean*mean);p.swap(next);
  }
 }
 std::ofstream out(argv[2],std::ios::binary);out.write((char*)results.data(),results.size()*sizeof(double));
 if(!out)throw std::runtime_error("write failed");
 std::cout<<"grid="<<M<<" trials="<<B<<" steps="<<K<<" first_prior_mean="<<std::setprecision(16)<<first_mean<<"\n";
}
