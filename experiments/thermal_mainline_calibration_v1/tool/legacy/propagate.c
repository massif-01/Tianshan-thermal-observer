/* Exact affine G1/G2 propagation. No inverse of A, no Euler integration. */
#include <math.h>
#include <stddef.h>

static double phi(double z, double dt) {
    return fabs(z*dt)<1e-8 ? dt*(1+z*dt/2+z*z*dt*dt/6) : expm1(z*dt)/z;
}

static void step(int model,const double *p,double E,const double *u,double dt,double *x) {
    if(model==1) {
        double k=p[0]+p[1]*u[2], q=p[2]*u[0]+p[3]*u[1];
        x[0] += phi(-k,dt)*(q-k*(x[0]-E));
        return;
    }
    double a=p[0],c=p[1],d=p[2]+p[3]*u[2];
    double A[4]={-a,a,c,-c-d};
    double v[2]={-a*(x[0]-x[1])+p[4]*u[0]+p[5]*u[1], c*(x[0]-x[1])-d*(x[1]-E)};
    double norm=(2*a+2*c+d)*dt;
    /* x_new=x+integral exp(A*s) ds * (A*x+f). Stable at tiny dt. */
    if(norm<0.1) {
        double t0=dt*v[0],t1=dt*v[1],q0=t0,q1=t1;
        for(int k=2;k<=12;k++) {
            double n0=dt*(A[0]*t0+A[1]*t1)/k;
            double n1=dt*(A[2]*t0+A[3]*t1)/k;
            t0=n0;t1=n1;q0+=n0;q1+=n1;
        }
        x[0]+=q0;x[1]+=q1;return;
    }
    double sum=a+c+d, disc=sqrt((a-c-d)*(a-c-d)+4*a*c);
    double lo=-(sum+disc)/2, hi=-2*a*d/(sum+disc);
    double fl=phi(lo,dt), fh=phi(hi,dt), slope;
    if(disc>1e-7*fmax(1.,sum)) slope=(fh-fl)/disc;
    else {
        double mid=(hi+lo)/2,z=mid*dt;
        slope=(exp(z)*(z-1)+1)/(mid*mid);
    }
    double q0=fl*v[0]+slope*((A[0]-lo)*v[0]+A[1]*v[1]);
    double q1=fl*v[1]+slope*(A[2]*v[0]+(A[3]-lo)*v[1]);
    x[0]+=q0;x[1]+=q1;
}

void trajectory(int model,size_t n,const double *p,double E,const double *dt,const double *inputs,const double *initial,double *out) {
    double x[2]={initial[0],initial[1]};out[0]=x[0];out[1]=x[1];
    for(size_t i=0;i<n;i++) {
        step(model,p,E,inputs+3*i,dt[i],x);
        out[2*(i+1)]=x[0];out[2*(i+1)+1]=x[1];
    }
}
