
from __future__ import absolute_import, print_function
from medusa import ver

print('\nSimple display of versions')
print(ver.version)  # current version can be imported into the package namespace to make it directly available
print(ver.test.version)  # or it can be merged as a package without an explicit version name for the "current" version
print(ver.test_v0.version)  # or you can have each available version imported separately
print(ver.test_v1.version)
print(ver.test_v1_0.version)
print(ver.test_v1.version)  # this shows that the modification in v1_0 did not change the v1 version

print('\nBe careful with mutables!!')
print(ver.failed_list)
print(ver.test.failed_list)  # not a mutable, so no modification
print(ver.test_v0.failed_list)  # all the changes to the mutable, though...
print(ver.test_v1.failed_list)  # have been mirrored to all the modules
print(ver.test_v1_0.failed_list)
print(ver.test_v1.failed_list)

print('\nSafer mutables using typecasting')
# typecasting the mutable is a safer alternative as it makes it a copy of the original
print(ver.better_list)
print(ver.test.better_list)
print(ver.test_v0.better_list)
print(ver.test_v1.better_list)
print(ver.test_v1_0.better_list)
print(ver.test_v1.better_list)

print('\nStill be careful with nested mutables!!!')  # the nested mutable is not a copy! it is just a shared reference across all the mutables
# nest a mutable
ver.better_list.append(['g', 'h', 'i'])
# both change
print(ver.better_list)
print(ver.test_v1_0.better_list)

print('\nThinking that the typecast will fix all problems...')
be_careful = list(ver.better_list)
be_careful.append('z')

print(be_careful)
print(ver.better_list)
print(ver.test_v1_0.better_list)

print('\n...may lead to some surprising problems!')
ver.better_list[-1].append('WTF?!?')
print(be_careful)
print(ver.better_list)
print(ver.test_v1_0.better_list)

print('\nKeep in mind these problems with mutables are not exclusive to these types of imports,'
      '\nbut these imports can mask the source problem, making it difficult to notice these issues.')
