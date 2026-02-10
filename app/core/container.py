"""향상된 의존성 주입 컨테이너"""
import inspect
from functools import lru_cache
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar('T')


class DIContainer:
    """의존성 주입 컨테이너
    
    Features:
    - 자동 의존성 해결
    - 싱글톤 인스턴스 관리
    - 순환 의존성 감지
    - 타입 힌트 기반 주입
    """
    
    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}
        self._resolving: set = set()  # 순환 의존성 감지
    
    def register(self, interface: Type[T], implementation: Type[T] = None, factory: Callable[[], T] = None, singleton: bool = True):
        """서비스 등록
        
        Args:
            interface: 인터페이스 타입
            implementation: 구현 클래스 (factory가 없을 경우)
            factory: 팩토리 함수
            singleton: 싱글톤 여부
        """
        if factory:
            service_factory = factory
        elif implementation:
            def service_factory():
                return self._create_instance(implementation)
        else:
            # 인터페이스와 구현이 같은 경우
            def service_factory():
                return self._create_instance(interface)
        
        if singleton:
            service_factory = lru_cache(maxsize=1)(service_factory)
        
        self._services[interface] = service_factory
    
    def get(self, service_type: Type[T]) -> T:
        """서비스 인스턴스 가져오기
        
        Args:
            service_type: 서비스 타입
            
        Returns:
            서비스 인스턴스
            
        Raises:
            ValueError: 서비스가 등록되지 않은 경우
            RuntimeError: 순환 의존성이 감지된 경우
        """
        if service_type in self._resolving:
            from app.core.error_management import DependencyException
            raise DependencyException(
                message=f"Circular dependency detected for {service_type.__name__}",
                service_type=service_type.__name__
            )
        
        if service_type not in self._services:
            from app.core.error_management import DependencyException
            raise DependencyException(
                message=f"Service {service_type.__name__} is not registered",
                service_type=service_type.__name__
            )
        
        self._resolving.add(service_type)
        try:
            instance = self._services[service_type]()
            return instance
        finally:
            self._resolving.discard(service_type)
    
    def _create_instance(self, cls: Type[T]) -> T:
        """클래스 인스턴스 생성 (자동 의존성 주입)
        
        Args:
            cls: 클래스 타입
            
        Returns:
            클래스 인스턴스
        """
        # 생성자 시그니처 분석
        signature = inspect.signature(cls.__init__)
        kwargs = {}
        
        for name, param in signature.parameters.items():
            if name == 'self':
                continue
                
            # 타입 힌트가 있는 경우 자동 주입
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[name] = self.get(param.annotation)
                except ValueError:
                    # 의존성을 찾을 수 없는 경우 기본값 사용
                    if param.default != inspect.Parameter.empty:
                        kwargs[name] = param.default
                    else:
                        from app.core.error_management import DependencyException
                        raise DependencyException(
                            message=f"Cannot resolve dependency {param.annotation.__name__} for {cls.__name__}",
                            service_type=cls.__name__
                        )
        
        return cls(**kwargs)
    
    def clear(self):
        """컨테이너 초기화"""
        self._services.clear()
        self._instances.clear()
        self._resolving.clear()
    
    def is_registered(self, service_type: Type) -> bool:
        """서비스 등록 여부 확인"""
        return service_type in self._services
    
    def get_registered_services(self) -> Dict[Type, Callable]:
        """등록된 모든 서비스 반환"""
        return self._services.copy()


# 글로벌 컨테이너 인스턴스
container = DIContainer()


